// The Calendar's image of a month's holidays, to download or share as a notice (admin and teachers).
// Drawn in the browser, so the server does no extra work. Uses the month and holidays calendar.js has on screen.

const IMAGE_SIZE = 1080; // a square fits Facebook and group chats
const HEADER_HEIGHT = 300;
const FOOTER_HEIGHT = 90;
const IMAGE_MARGIN = 70;
const LARGEST_ROW = 150;
const MOST_ROWS = 6; // more than this and the text gets too small to read on a phone
const IMAGE_FONT = "\"Plus Jakarta Sans\", system-ui, sans-serif";

// Fixed colours: a posted image must look the same whichever theme the person who made it is using.
const IMAGE_ACCENT_FROM = "#4f46e5";
const IMAGE_ACCENT_TO = "#06b6d4";
const IMAGE_BACKGROUND = "#ffffff";
const IMAGE_TEXT = "#1f2937";
const IMAGE_MUTED = "#6b7280";
const IMAGE_ON_ACCENT = "#ffffff";
const KIND_COLOURS = { // the same meaning as the calendar's badges: [box, text on the box]
  regular: ["#dc3545", "#ffffff"],
  special: ["#ffc107", "#212529"],
  "special-working": ["#0dcaf0", "#212529"],
  local: ["#198754", "#ffffff"],
};

const imageModalElement = document.getElementById("image-modal");
const imageButton = document.getElementById("share-image-button");
const imagePreview = document.getElementById("image-preview");
const imageEmpty = document.getElementById("image-empty");
const imageDownload = document.getElementById("image-download");
const imageShare = document.getElementById("image-share");
let imageFile = null;

// loadImage("/static/img/logo.png") -> a promise of the loaded picture
const loadImage = (source) => new Promise((resolve, reject) => {
  const picture = new Image();
  picture.onload = () => resolve(picture);
  picture.onerror = reject;
  picture.src = source;
});

// wrapText(context, "A long name", 500, 2) -> at most 2 lines that fit in 500 pixels, the last one cut with "..."
function wrapText(context, text, width, most) {
  const lines = [];
  let line = "";
  for (const word of text.split(" ")) {
    const longer = line ? `${line} ${word}` : word;
    if (context.measureText(longer).width <= width || !line) {
      line = longer;
    } else {
      lines.push(line);
      line = word;
    }
  }
  lines.push(line);
  if (lines.length <= most) return lines;
  const kept = lines.slice(0, most);
  while (kept[most - 1] && context.measureText(`${kept[most - 1]}...`).width > width) {
    kept[most - 1] = kept[most - 1].slice(0, -1);
  }
  kept[most - 1] += "...";
  return kept;
}

function roundedBox(context, x, y, width, height, radius) {
  context.beginPath();
  if (context.roundRect) context.roundRect(x, y, width, height, radius);
  else context.rect(x, y, width, height); // older browsers: square corners are fine
  context.fill();
}

function drawHeader(context, logo, monthTitle) {
  const gradient = context.createLinearGradient(0, 0, IMAGE_SIZE, HEADER_HEIGHT);
  gradient.addColorStop(0, IMAGE_ACCENT_FROM);
  gradient.addColorStop(1, IMAGE_ACCENT_TO);
  context.fillStyle = gradient;
  context.fillRect(0, 0, IMAGE_SIZE, HEADER_HEIGHT);
  const logoHeight = 60;
  context.drawImage(logo, IMAGE_MARGIN, 45, logoHeight * (logo.width / logo.height), logoHeight);
  context.fillStyle = IMAGE_ON_ACCENT;
  context.textBaseline = "alphabetic";
  context.textAlign = "left";
  context.font = `700 76px ${IMAGE_FONT}`;
  context.fillText(monthTitle, IMAGE_MARGIN, 195);
  context.font = `500 36px ${IMAGE_FONT}`;
  context.fillText(t("Holidays this month"), IMAGE_MARGIN, 250);
}

// One holiday: a coloured box with the weekday and day, then the name and kind. scale shrinks a row when many fit.
function drawRow(context, holiday, top, height, scale) {
  const date = parseDay(holiday.day);
  const [boxColour, boxText] = KIND_COLOURS[holiday.kind];
  const boxSize = height - 24 * scale;
  const boxTop = top + 12 * scale;
  context.fillStyle = boxColour;
  roundedBox(context, IMAGE_MARGIN, boxTop, boxSize, boxSize, 20 * scale);
  context.fillStyle = boxText;
  context.textAlign = "center";
  context.font = `600 ${Math.round(24 * scale)}px ${IMAGE_FONT}`;
  context.fillText(date.toLocaleDateString(undefined, { weekday: "short" }), IMAGE_MARGIN + boxSize / 2, boxTop + boxSize * 0.34);
  context.font = `700 ${Math.round(52 * scale)}px ${IMAGE_FONT}`;
  context.fillText(String(date.getDate()), IMAGE_MARGIN + boxSize / 2, boxTop + boxSize * 0.8);

  const textLeft = IMAGE_MARGIN + boxSize + 30 * scale;
  const nameSize = Math.round(38 * scale);
  context.textAlign = "left";
  context.fillStyle = IMAGE_TEXT;
  context.font = `700 ${nameSize}px ${IMAGE_FONT}`;
  const lines = wrapText(context, holiday.name, IMAGE_SIZE - textLeft - IMAGE_MARGIN, 2);
  const lineHeight = nameSize * 1.2;
  const textHeight = lines.length * lineHeight + 34 * scale;
  let baseline = top + (height - textHeight) / 2 + nameSize;
  for (const line of lines) {
    context.fillText(line, textLeft, baseline);
    baseline += lineHeight;
  }
  context.fillStyle = IMAGE_MUTED;
  context.font = `500 ${Math.round(26 * scale)}px ${IMAGE_FONT}`;
  context.fillText(t(KIND_LABEL[holiday.kind]), textLeft, baseline + 4 * scale);
}

// Returns a promise of the PNG of these holidays.
async function makeHolidayImage(holidays, monthTitle, generatedBy) {
  const canvas = document.createElement("canvas");
  canvas.width = IMAGE_SIZE;
  canvas.height = IMAGE_SIZE;
  const context = canvas.getContext("2d");
  // A canvas does not wait for a web font by itself; without this the first image could use the fallback font.
  try {
    await Promise.all([500, 600, 700].map((weight) => document.fonts.load(`${weight} 40px "Plus Jakarta Sans"`)));
  } catch {
    // The fallback font still gives a good image.
  }
  const logo = await loadImage("/static/img/logo-white.png");

  context.fillStyle = IMAGE_BACKGROUND;
  context.fillRect(0, 0, IMAGE_SIZE, IMAGE_SIZE);
  drawHeader(context, logo, monthTitle);

  const hidden = holidays.length > MOST_ROWS ? holidays.length - (MOST_ROWS - 1) : 0;
  const shown = hidden ? holidays.slice(0, MOST_ROWS - 1) : holidays;
  const rows = shown.length + (hidden ? 1 : 0);
  const space = IMAGE_SIZE - HEADER_HEIGHT - FOOTER_HEIGHT - 40;
  const rowHeight = Math.min(LARGEST_ROW, space / rows);
  const scale = rowHeight / LARGEST_ROW;
  shown.forEach((holiday, index) => drawRow(context, holiday, HEADER_HEIGHT + 30 + index * rowHeight, rowHeight, scale));
  if (hidden) {
    context.fillStyle = IMAGE_MUTED;
    context.textAlign = "left";
    context.font = `600 ${Math.round(32 * scale)}px ${IMAGE_FONT}`;
    context.fillText(t("and {count} more", { count: hidden }), IMAGE_MARGIN, HEADER_HEIGHT + 30 + shown.length * rowHeight + rowHeight / 2);
  }

  context.fillStyle = IMAGE_MUTED;
  context.textAlign = "center";
  context.font = `500 24px ${IMAGE_FONT}`;
  context.fillText(generatedBy, IMAGE_SIZE / 2, IMAGE_SIZE - 40);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

async function openHolidayImage() {
  const stopLoading = startLoading(imageButton);
  if (!stopLoading) return;
  hideError("image-error");
  const prefix = isoDay(shownYear, shownMonth, 1).slice(0, 7);
  const holidays = (loadedYears[shownYear] || []).filter((holiday) => holiday.day.startsWith(prefix));
  const monthTitle = new Date(shownYear, shownMonth, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
  imageEmpty.classList.toggle("d-none", holidays.length > 0);
  for (const piece of [imagePreview, imageDownload, imageShare]) piece.classList.add("d-none");
  try {
    if (holidays.length) {
      const blob = await makeHolidayImage(holidays, monthTitle, imageButton.dataset.generatedBy);
      const name = `Holidays - ${monthTitle}.png`;
      imageFile = new File([blob], name, { type: "image/png" });
      if (imagePreview.src) URL.revokeObjectURL(imagePreview.src);
      imagePreview.src = URL.createObjectURL(blob);
      imagePreview.alt = `${t("Holidays this month")}: ${monthTitle}`;
      imagePreview.classList.remove("d-none");
      imageDownload.href = imagePreview.src;
      imageDownload.download = name;
      imageDownload.classList.remove("d-none");
      // Computers mostly cannot share a file to an app, so the button only shows where it works.
      imageShare.classList.toggle("d-none", !(navigator.canShare && navigator.canShare({ files: [imageFile] })));
    }
    bootstrap.Modal.getOrCreateInstance(imageModalElement).show();
  } catch {
    showError("calendar-error", t("Could not make the image."));
  } finally {
    stopLoading();
  }
}

imageButton.addEventListener("click", openHolidayImage);

imageShare.addEventListener("click", async () => {
  try {
    await navigator.share({ files: [imageFile] });
  } catch (problem) {
    // Closing the phone's share menu is not a problem; anything else is.
    if (problem.name !== "AbortError") showError("image-error", t("Could not share the image. Download it instead."));
  }
});
