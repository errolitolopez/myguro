"""Philippine holidays: the national ones worked out from the year, and the rules for a local holiday."""

from datetime import date, timedelta

from myguro.errors import ValidationError

MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 300  # a few sentences; the admin's note for a local holiday
MIN_YEAR = 2000  # the calendar page and the API stay inside a sane range
MAX_YEAR = 2100
MIN_SEARCH_LENGTH = 2  # one letter matches nearly everything
MAX_SEARCH_RESULTS = 30  # enough to choose from on a phone

# What kind of day it is. "local" holidays are the ones the admin adds.
REGULAR = "regular"  # regular holiday: no classes
SPECIAL = "special"  # special non-working day: no classes
SPECIAL_WORKING = "special-working"  # a special day, but school goes on
LOCAL = "local"
KINDS = (REGULAR, SPECIAL, SPECIAL_WORKING, LOCAL)

# Fixed dates: (month, day, name, kind).
FIXED = [
    (1, 1, "New Year's Day", REGULAR),
    (2, 25, "EDSA People Power Revolution Anniversary", SPECIAL_WORKING),
    (4, 9, "Araw ng Kagitingan", REGULAR),
    (5, 1, "Labor Day", REGULAR),
    (6, 12, "Independence Day", REGULAR),
    (8, 21, "Ninoy Aquino Day", SPECIAL),
    (11, 1, "All Saints' Day", SPECIAL),
    (11, 30, "Bonifacio Day", REGULAR),
    (12, 8, "Feast of the Immaculate Conception", SPECIAL),
    (12, 24, "Christmas Eve", SPECIAL),
    (12, 25, "Christmas Day", REGULAR),
    (12, 30, "Rizal Day", REGULAR),
    (12, 31, "New Year's Eve", SPECIAL),
]


# What each national holiday is about, in one or two sentences a student can read. English here; the Taglish is
# in i18n/tl_admin.py, keyed by the same sentence, and the page's JavaScript translates it.
DESCRIPTIONS = {
    "New Year's Day": "Marks the first day of the new year. Families gather and welcome it with noise and round "
                      "fruits, a Filipino tradition for good luck.",
    "EDSA People Power Revolution Anniversary": "Remembers the peaceful People Power Revolution of 1986, when "
                                                "millions of Filipinos gathered on EDSA, ended the rule of "
                                                "Ferdinand Marcos and brought back democracy.",
    "Araw ng Kagitingan": "The Day of Valor. It honors the Filipino and American soldiers who fought in the Battle "
                          "of Bataan in 1942, and those who suffered in the Bataan Death March that followed.",
    "Labor Day": "Honors Filipino workers and what they give to the country. Workers around the world celebrate it "
                 "on the same day.",
    "Independence Day": "Remembers June 12, 1898, when Emilio Aguinaldo declared the independence of the "
                        "Philippines from Spain in Kawit, Cavite.",
    "Ninoy Aquino Day": "Remembers Senator Benigno \"Ninoy\" Aquino Jr., who was shot on August 21, 1983 when he "
                        "came home. His death moved many Filipinos to join the movement that led to People Power.",
    "All Saints' Day": "Filipinos visit the graves of their loved ones, clean them, and leave flowers and candles "
                       "to pray for them. The next day, November 2, is All Souls' Day.",
    "Bonifacio Day": "Honors Andres Bonifacio, born on November 30, 1863, who founded the Katipunan and is called "
                     "the Father of the Philippine Revolution.",
    "Feast of the Immaculate Conception": "A Catholic feast in honor of the Virgin Mary, who is the patroness of "
                                          "the Philippines.",
    "Christmas Eve": "The night before Christmas. Families go to the last night mass, called Simbang Gabi, and share "
                     "Noche Buena, a feast at midnight.",
    "Christmas Day": "Celebrates the birth of Jesus Christ. Filipinos spend it with family, gifts and food, and the "
                     "Christmas season starts as early as September.",
    "Rizal Day": "Remembers Dr. José Rizal, our national hero, who was executed on December 30, 1896. His novels "
                 "Noli Me Tangere and El Filibusterismo woke Filipinos to seek freedom.",
    "New Year's Eve": "The last day of the year. Families share Media Noche, a meal at midnight, and welcome the "
                      "new year with noise, lights and fireworks.",
    "Maundy Thursday": "Part of Holy Week. It remembers the Last Supper of Jesus with his apostles. Many Filipinos "
                       "do Visita Iglesia, visiting several churches to pray.",
    "Good Friday": "Remembers the suffering and death of Jesus on the cross. It is a quiet day of prayer and "
                   "fasting, with processions and the Way of the Cross.",
    "Black Saturday": "The day between Good Friday and Easter Sunday, when Jesus lay in the tomb. It is a day of "
                      "quiet waiting before Easter.",
    "National Heroes Day": "Honors all the heroes, known and unknown, who fought for the freedom of the "
                           "Philippines. It is held on the last Monday of August.",
}


def easter_sunday(year):
    """Easter Sunday of a year (the usual Gregorian calendar calculation)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def last_monday(year, month):
    """The last Monday of a month (National Heroes Day is the last Monday of August)."""
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return last - timedelta(days=last.weekday())


def national_holidays(year):
    """The national holidays of a year as [{"day": "2026-04-03", "name": ..., "kind": ...}], by date.
    Days set by a yearly proclamation (Eid'l Fitr, Eid'l Adha, Chinese New Year, one-off days) are not here:
    the admin adds those as local holidays."""
    found = [(date(year, month, day), name, kind) for month, day, name, kind in FIXED]
    easter = easter_sunday(year)
    found += [(easter - timedelta(days=3), "Maundy Thursday", REGULAR),
              (easter - timedelta(days=2), "Good Friday", REGULAR),
              (easter - timedelta(days=1), "Black Saturday", SPECIAL),
              (last_monday(year, 8), "National Heroes Day", REGULAR)]
    return [{"day": day.isoformat(), "name": name, "kind": kind, "description": DESCRIPTIONS[name]}
            for day, name, kind in sorted(found)]


def check_year(value):
    """The year to show, as a number between MIN_YEAR and MAX_YEAR."""
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Choose a valid year.") from None
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValidationError("Choose a valid year.")
    return year


def check_day(value):
    """A date from the request as "YYYY-MM-DD". Raises ValidationError when it is not a real day in range."""
    try:
        parsed = date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else None
    except ValueError:
        parsed = None
    if parsed is None or not MIN_YEAR <= parsed.year <= MAX_YEAR:
        raise ValidationError("Choose a valid date.")
    return parsed.isoformat()


def check_holiday(data):
    """(day, name, description) of a local holiday from the request; the description is optional ("" for none).
    Raises ValidationError with a short message."""
    day = check_day(data.get("day"))
    name = " ".join(data.get("name").split()) if isinstance(data.get("name"), str) else ""
    if not name:
        raise ValidationError("Type the name of the holiday.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"The name can be at most {MAX_NAME_LENGTH} characters.")
    description = " ".join(data.get("description").split()) if isinstance(data.get("description"), str) else ""
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"The description can be at most {MAX_DESCRIPTION_LENGTH} characters.")
    return day, name, description
