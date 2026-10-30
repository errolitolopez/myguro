"""Taglish: Tagalog with the everyday English words kept, the way people really talk.

Each key is the English sentence exactly as it is written in a page; the value is its Taglish. {name} is a
value the page fills in, and must be in both. A sentence with no entry here shows in English.
Keep in English: activity, score, submit, due, class, subject, teacher, password, login, and other words
people say in English. "po" only where a message speaks politely to the person, and only a little.
"""

TAGLISH = {
    # --- Shared: navbar, footer, quick jump ---
    "Dashboard": "Dashboard",
    "Users": "Users",
    "Schedule": "Schedule",
    "Log": "Log",
    "Activities": "Activities",
    "Classes": "Classes",
    "Language": "Language",
    "Theme": "Theme",
    "Change language": "Palitan ang language",
    "Change theme": "Palitan ang theme",
    "Account menu": "Account menu",
    "School year": "School year",
    "(current)": "(ngayon)",
    "Display": "Display",
    "Feedback": "Feedback",
    "Settings": "Settings",
    "Password": "Password",
    "Recovery code": "Recovery code",
    "Logout": "Mag-logout",
    "You are looking at the school year {year}. It is over, so nothing can be changed.":
        "Tinitingnan mo ang school year {year}. Tapos na ito, kaya wala nang mababago.",
    "Quick jump (Ctrl+K)": "Mabilis na lipat (Ctrl+K)",
    "Quick jump": "Mabilis na lipat",
    "Jump to...": "Lumipat sa...",
    "Search pages, classes and activities": "Maghanap ng pages, classes at activities",
    "Arrow keys to move · Enter to open · Esc to close": "Arrow keys para gumalaw · Enter para buksan · Esc para isara",
    "Page": "Page",
    "Class": "Class",
    "Activity": "Activity",
    "Nothing found.": "Walang nahanap.",
    "MyGuro is a free, non-profit tool for schools.": "Ang MyGuro ay libre at non-profit na tool para sa mga school.",
    # --- Login, forgot password, change password ---
    "Login": "Login",
    "Learning Management System": "Learning Management System",
    "Username": "Username",
    "Show password": "Ipakita ang password",
    "Hide password": "Itago ang password",
    "Forgot your password?": "Nakalimutan mo ba ang password mo?",
    "Forgot password": "Nakalimutan ang password",
    "No account? Ask the admin to create one.": "Wala pang account? Magtanong sa admin para gumawa ng account.",
    "Enter your username and password.": "Ilagay ang username at password mo.",
    "Login failed.": "Hindi nakapag-login.",
    "Cannot reach the server. Check your connection.": "Hindi maabot ang server. Tingnan ang connection mo.",
    "Type your username and your recovery code, then choose a new password.":
        "I-type ang username at recovery code mo, tapos pumili ng bagong password.",
    "New password": "Bagong password",
    "Type the new password again": "I-type ulit ang bagong password",
    "Change my password": "Palitan ang password ko",
    "Go to login": "Pumunta sa login",
    "No recovery code? Ask the admin to reset your password.":
        "Walang recovery code? Magtanong sa admin para i-reset ang password mo.",
    "Back to login": "Balik sa login",
    "Enter your username and your recovery code.": "Ilagay ang username at recovery code mo.",
    "New password must be at least {min} characters.": "Ang bagong password ay dapat hindi bababa sa {min} na characters.",
    "The two new passwords don't match.": "Hindi magkatugma ang dalawang bagong password.",
    "Could not change the password.": "Hindi napalitan ang password.",
    "Your password was changed. Your recovery code can be used 1 more time.":
        "Napalitan na ang password mo. Magagamit mo pa ang recovery code mo ng 1 beses.",
    "Your password was changed. Your recovery code can be used {count} more times.":
        "Napalitan na ang password mo. Magagamit mo pa ang recovery code mo ng {count} beses.",
    "Your password was changed. Your recovery code is used up now: log in and make a new one.":
        "Napalitan na ang password mo. Ubos na ang gamit ng recovery code mo: mag-login at gumawa ng bago.",
    "Change password": "Palitan ang password",
    "Hi {name}! You're using a temporary password. Choose your own to continue.":
        "Hi {name}! Temporary password ang gamit mo. Pumili ng sarili mong password para magpatuloy.",
    "Current password": "Kasalukuyang password",
    "At least 6 characters.": "Hindi bababa sa 6 na characters.",
    "Save password": "I-save ang password",
    "Back to dashboard": "Balik sa dashboard",
    "Enter your current password.": "Ilagay ang kasalukuyang password mo.",
    "Could not save the password.": "Hindi na-save ang password.",
    # --- Recovery code ---
    "Your password is set. One more step: make a recovery code, so you can reset your password yourself if you forget it.":
        "Naka-set na ang password mo. Isang hakbang na lang: gumawa ng recovery code, para ikaw mismo ang makapag-reset ng password kapag nakalimutan mo ito.",
    "If you forget your password, this code lets you choose a new one without asking the admin. It is long and random, so nobody can guess it, and it works 3 times; after that you make a new one. Save it somewhere safe, like your phone's notes or a password manager. Anyone who has it can reset your password, so don't share it.":
        "Kapag nakalimutan mo ang password mo, gamit ang code na ito ay makakapili ka ng bago nang hindi na nagtatanong sa admin. Mahaba at random ito, kaya walang makakahula, at 3 beses lang itong gumagana; pagkatapos, gagawa ka ng bago. I-save ito sa ligtas na lugar, gaya ng notes sa phone mo o password manager. Kahit sino na may hawak nito ay makakapag-reset ng password mo, kaya huwag mo itong ibigay sa iba.",
    "Make a new code": "Gumawa ng bagong code",
    "Make a recovery code": "Gumawa ng recovery code",
    "Your current password": "Ang kasalukuyang password mo",
    "Making a new code stops the old one from working.": "Kapag gumawa ka ng bagong code, hindi na gagana ang luma.",
    "Replace your recovery code?": "Papalitan ba ang recovery code mo?",
    "Close": "Isara",
    "Your old code will stop working right away. If you saved it somewhere, that copy will not work any more. You will get a new code to save.":
        "Titigil agad ang pag-gana ng lumang code mo. Kung may na-save kang kopya, hindi na ito gagana. Bibigyan ka ng bagong code na isi-save.",
    "Keep my old code": "Panatilihin ang lumang code",
    "Replace it": "Palitan ito",
    "Could not load your recovery code.": "Hindi na-load ang recovery code mo.",
    "Could not make the code.": "Hindi nagawa ang code.",
    "You have a recovery code (made {day}). It can be used 1 more time to reset your password.":
        "May recovery code ka (ginawa noong {day}). Magagamit pa ito ng 1 beses para i-reset ang password mo.",
    "You have a recovery code (made {day}). It can be used {count} more times to reset your password.":
        "May recovery code ka (ginawa noong {day}). Magagamit pa ito ng {count} beses para i-reset ang password mo.",
    "Your recovery code is used up. Make a new one.": "Ubos na ang gamit ng recovery code mo. Gumawa ng bago.",
    "You don't have a recovery code yet.": "Wala ka pang recovery code.",
    "Your recovery code": "Ang recovery code mo",
    "Copy": "Kopyahin",
    "Copied": "Nakopya na",
    "Select the code and copy it": "I-select ang code at kopyahin ito",
    "Download": "I-download",
    "This code is shown only once and hides itself in {seconds} seconds. Save it now, for example in your phone's notes or a password manager. Anyone who has it can reset your password, so don't share it.":
        "Isang beses lang ipinapakita ang code na ito at kusa itong nagtatago sa loob ng {seconds} segundo. I-save na ito ngayon, halimbawa sa notes ng phone mo o sa password manager. Kahit sino na may hawak nito ay makakapag-reset ng password mo, kaya huwag mo itong ibigay sa iba.",
    "Hiding in 1 second.": "Magtatago sa loob ng 1 segundo.",
    "Hiding in {count} seconds.": "Magtatago sa loob ng {count} segundo.",
    "The code is hidden now and is not shown again. If you did not save it, make a new one (account menu, Recovery code).":
        "Nakatago na ang code at hindi na ito ipapakita ulit. Kung hindi mo ito na-save, gumawa ng bago (account menu, Recovery code).",
    # --- Student dashboard ---
    "Hi, {name}!": "Hi, {name}!",
    "You don't have a working recovery code. Without one, only the admin can reset your password.":
        "Wala kang gumaganang recovery code. Kung wala nito, admin lang ang makakapag-reset ng password mo.",
    "Make one now": "Gumawa na ngayon",
    "To do": "Gagawin pa",
    "Submitted": "Na-submit",
    "Loading...": "Naglo-load...",
    "Next due": "Susunod na due",
    "Progress": "Progress",
    "Score trend": "Score trend",
    "Subjects": "Subjects",
    "Average score": "Average na score",
    "Done": "Tapos na",
    "Chart values": "Mga value ng chart",
    "Name": "Pangalan",
    "Value": "Value",
    "Show in the chart": "Ipakita sa chart",
    "Bar chart of results": "Bar chart ng mga resulta",
    "My scores": "Mga score ko",
    "Due today": "Due ngayon",
    "Due tomorrow": "Due bukas",
    "Due in {days} days": "Due sa {days} araw",
    "Overdue by 1 day": "Lampas na ng 1 araw",
    "Overdue by {days} days": "Lampas na ng {days} araw",
    "{answered} of {questions} answered": "{answered} sa {questions} ang nasagot",
    "No due date": "Walang due date",
    "Continue": "Ituloy",
    "Start": "Simulan",
    "You're all caught up. Nothing to do right now.": "Tapos mo na lahat! Wala nang gagawin ngayon.",
    "Could not load your activities.": "Hindi na-load ang mga activity mo.",
    "Nothing given yet": "Wala pang ibinigay",
    "{done} of 1 activity done": "{done} sa 1 activity ang tapos na",
    "{done} of {total} activities done": "{done} sa {total} activities ang tapos na",
    "{count} submitted this week": "{count} ang na-submit ngayong linggo",
    "Scores show here once your teacher releases them.": "Lalabas dito ang mga score kapag inilabas na ng teacher mo.",
    "Your latest score": "Ang pinakabago mong score",
    "Same as the one before": "Pareho sa nauna",
    "Up {n}% from the one before": "Tumaas ng {n}% mula sa nauna",
    "Down {n}% from the one before": "Bumaba ng {n}% mula sa nauna",
    "Your last scores: {scores}": "Ang mga huli mong score: {scores}",
    "All done, great job!": "Tapos na lahat, galing!",
    "No subject": "Walang subject",
    "Your scores will show here after you submit an activity.": "Lalabas dito ang mga score mo pagkatapos mong mag-submit ng activity.",
    "Your average score in each subject (only scores your teacher has released). Tap a bar to see its activities.":
        "Ang average na score mo sa bawat subject (mga score lang na inilabas na ng teacher mo). I-tap ang bar para makita ang mga activity.",
    "Activities you finished in each subject. Tap a bar to see them.":
        "Mga activity na natapos mo sa bawat subject. I-tap ang bar para makita ang mga ito.",
    "No released scores yet": "Wala pang inilabas na score",
    "Average {percent}%": "Average na {percent}%",
    "1 activity done": "1 activity ang tapos na",
    "{count} activities done": "{count} activities ang tapos na",
    "{subject}: your score on each activity. Tap a bar to open it.":
        "{subject}: ang score mo sa bawat activity. I-tap ang bar para buksan.",
    "Score not released yet": "Hindi pa inilalabas ang score",
    "Could not load the chart.": "Hindi na-load ang chart.",
    "The chart could not load. Check your internet connection.": "Hindi na-load ang chart. Tingnan ang internet connection mo.",
    # Tips and the feedback pop-up
    "Tip: ": "Tip: ",
    "Don't show tips": "Huwag nang ipakita ang tips",
    "Close tip": "Isara ang tip",
    "Your answers save as you go. You can also tap Save progress.":
        "Kusang nase-save ang mga sagot mo habang nagsasagot ka. Puwede mo ring i-tap ang Save progress.",
    "You can submit only once per try, so check for unanswered questions first.":
        "Isang beses ka lang puwedeng mag-submit sa bawat try, kaya tingnan muna kung may hindi pa nasasagot.",
    "Some activities let you try again after you submit.": "May mga activity na puwede mong ulitin pagkatapos mong mag-submit.",
    "Your score can stay hidden until your teacher releases it.": "Maaaring nakatago ang score mo hanggang ilabas ito ng teacher mo.",
    "Late work is still accepted. It is marked Late.": "Tinatanggap pa rin ang late na gawa. Mamarkahan itong Late.",
    "How is MyGuro for you?": "Kumusta ang MyGuro para sa iyo?",
    "Tell us what you think. It takes less than a minute: a few questions, each rated 1 to 5 stars. Your answers are private.":
        "Sabihin sa amin ang iniisip mo. Wala pang isang minuto: ilang tanong na may rating na 1 hanggang 5 stars. Pribado ang mga sagot mo.",
    "Give feedback": "Magbigay ng feedback",
    "Maybe later": "Mamaya na lang",
    # --- My activities ---
    "My activities": "Mga activity ko",
    "Show": "Ipakita",
    "{answered} / {questions} answered": "{answered} / {questions} ang nasagot",
    "Closed": "Sarado",
    "+{pending} pts to check": "+{pending} pts na susuriin pa",
    "Paper": "Paper",
    "Late": "Late",
    "Trying again · attempt {attempt} · {progress}": "Inuulit · attempt {attempt} · {progress}",
    "Can try again": "Puwedeng ulitin",
    "Overdue · was due {day}": "Lampas na · due noong {day}",
    "Due {day}": "Due sa {day}",
    "In progress · {progress}": "Ginagawa pa · {progress}",
    "Not started yet": "Hindi pa nasisimulan",
    "Nothing submitted yet.": "Wala pang na-submit.",
    "Nothing to do. Great job!": "Wala nang gagawin. Galing!",
    "All subjects": "Lahat ng subjects",
    # --- The answer page ---
    "Activity": "Activity",
    "No answer": "Walang sagot",
    "True": "True",
    "False": "False",
    "Blank {number}": "Blank {number}",
    "Answer for item {number}": "Sagot para sa item {number}",
    "Write your answer here...": "Isulat dito ang sagot mo...",
    "Your answer": "Ang sagot mo",
    "Teacher's remark: ": "Remark ng teacher: ",
    "Not saved yet...": "Hindi pa na-save...",
    "Saved at {time}": "Na-save noong {time}",
    "Saving...": "Sine-save...",
    "Could not save.": "Hindi na-save.",
    "Not saved — check your connection": "Hindi na-save — tingnan ang connection mo",
    "1 pt": "1 pt",
    "{points} pts": "{points} pts",
    "(+{pending} to check)": "(+{pending} susuriin pa)",
    "Attempt {attempt} (no limit)": "Attempt {attempt} (walang limit)",
    "Attempt {attempt} of {max}": "Attempt {attempt} sa {max}",
    "{earned} / {possible} points": "{earned} / {possible} points",
    "{attempt}. Your last submitted score: {score}. Submitting again replaces it — your latest submission counts.":
        "{attempt}. Ang huli mong na-submit na score: {score}. Kapag nag-submit ka ulit, mapapalitan ito — ang pinakabago mong submission ang binibilang.",
    "Your score": "Score mo",
    "Your teacher will show the scores when everyone is done.": "Ipapakita ng teacher mo ang mga score kapag tapos na ang lahat.",
    "Scored by your teacher from your paper.": "Na-score ng teacher mo mula sa paper mo.",
    "1 more point from short answers: waiting for your teacher to check.":
        "1 pang point mula sa short answers: hinihintay na masuri ng teacher mo.",
    "{count} more points from short answers: waiting for your teacher to check.":
        "{count} pang points mula sa short answers: hinihintay na masuri ng teacher mo.",
    "Everything is checked.": "Tapos nang suriin ang lahat.",
    "{attempt} · you can try again": "{attempt} · puwede kang umulit",
    "{attempt} · 1 try left": "{attempt} · 1 try na lang",
    "{attempt} · {count} tries left": "{attempt} · {count} tries pa",
    "{attempt} · no tries left": "{attempt} · wala nang natitirang try",
    "All answers saved": "Na-save na ang lahat ng sagot",
    "Could not load the activity.": "Hindi na-load ang activity.",
    "This is your last try: you can't change your answers after submitting.":
        "Ito na ang huli mong try: hindi mo na mababago ang mga sagot mo pagkatapos mag-submit.",
    "After submitting you can still try again (no limit); your latest submission counts.":
        "Pagkatapos mag-submit, puwede ka pang umulit (walang limit); ang pinakabago mong submission ang binibilang.",
    "After submitting you can still try again (1 more try); your latest submission counts.":
        "Pagkatapos mag-submit, puwede ka pang umulit (1 pang try); ang pinakabago mong submission ang binibilang.",
    "After submitting you can still try again ({count} more tries); your latest submission counts.":
        "Pagkatapos mag-submit, puwede ka pang umulit ({count} pang tries); ang pinakabago mong submission ang binibilang.",
    "1 question has no answer yet.": "1 tanong ang wala pang sagot.",
    "{count} questions have no answer yet.": "{count} tanong ang wala pang sagot.",
    "Could not submit.": "Hindi na-submit.",
    "Cannot reach the server. Your answers are kept here; try again.":
        "Hindi maabot ang server. Nakatabi pa rito ang mga sagot mo; subukan ulit.",
    "Could not start again.": "Hindi nasimulan ulit.",
    "Submitted late": "Na-submit nang late",
    "Try again": "Ulitin",
    "This activity is closed. You can read the questions again to review, but you can't change your answers.":
        "Sarado na ang activity na ito. Puwede mong basahin ulit ang mga tanong para mag-review, pero hindi mo na mababago ang mga sagot mo.",
    "Your answers are hidden after you submit. You can still read the questions below.":
        "Nakatago ang mga sagot mo pagkatapos mong mag-submit. Mababasa mo pa rin ang mga tanong sa ibaba.",
    "Save progress": "I-save ang progress",
    "Submit": "Submit",
    "Submit your answers?": "I-submit na ba ang mga sagot mo?",
    "You can't change your answers after submitting.": "Hindi mo na mababago ang mga sagot mo pagkatapos mag-submit.",
    "Not yet": "Hindi pa",
    # --- Feedback ---
    "Rate MyGuro": "I-rate ang MyGuro",
    "Tap the stars: 1 is poor and 5 is excellent. Rate every question, then send. Your answers are private: the admin only sees totals, never who answered. You can send feedback once.":
        "I-tap ang mga star: 1 ang pinakamababa at 5 ang pinakamataas. I-rate ang bawat tanong, tapos i-send. Pribado ang mga sagot mo: totals lang ang nakikita ng admin, hindi kung sino ang sumagot. Isang beses ka lang puwedeng magpadala ng feedback.",
    "Thank you! Your feedback was sent.": "Salamat! Naipadala na ang feedback mo.",
    "You already sent your feedback. Thank you!": "Naipadala mo na ang feedback mo. Salamat!",
    "Send feedback": "Ipadala ang feedback",
    "{value} of {max}": "{value} sa {max}",
    "Could not load the questions.": "Hindi na-load ang mga tanong.",
    "Please rate every question.": "Paki-rate ang bawat tanong.",
    "Could not send your feedback.": "Hindi naipadala ang feedback mo.",
    # The questions people rate (they live in domain/feedback.py)
    "MyGuro is easy to use.": "Madaling gamitin ang MyGuro.",
    "The text is easy to read on my screen.": "Madaling basahin ang text sa screen ko.",
    "I know what to do on each page.": "Alam ko kung ano ang gagawin sa bawat page.",
    "I like how MyGuro looks.": "Gusto ko ang itsura ng MyGuro.",
    "Overall, how would you rate MyGuro?": "Sa kabuuan, ano ang rating mo sa MyGuro?",
    # --- Display ---
    "How MyGuro looks to you. These choices are saved in this browser only, so on another phone or computer you choose again.":
        "Kung paano lumalabas ang MyGuro para sa iyo. Sa browser na ito lang naka-save ang mga pinili mo, kaya sa ibang phone o computer ay pipili ka ulit.",
    "Reading": "Reading",
    "Effects": "Effects",
    "Glass blur and moving background": "Glass blur at gumagalaw na background",
    "Turn this off if pages feel slow or choppy, which can happen on a phone. Panels become plain and nothing moves behind them. Until you choose, phones start with it off and computers with it on.":
        "I-off ito kung mabagal o putol-putol ang mga page, na puwedeng mangyari sa phone. Magiging plain ang mga panel at walang gagalaw sa likod. Hangga't hindi ka pumipili, naka-off ito sa mga phone at naka-on sa mga computer.",
    "Menu": "Menu",
    "Menu bar at the bottom on phones": "Menu bar sa ibaba sa mga phone",
    "On: the menu is a bar at the bottom of the screen, within reach of your thumb. Off: the menu tabs show at the top, like on a computer. Wider screens always show them at the top.":
        "On: nasa ibaba ng screen ang menu bilang bar, abot ng hinlalaki mo. Off: nasa itaas ang mga menu tab, gaya sa computer. Ang mas malalapad na screen ay laging nasa itaas ang mga ito.",
    "Preview": "Preview",
    "Read the paragraph below and answer the questions that follow. A good reading text is easy on the eyes: the letters are big enough, the lines are not crowded, and the edges are tidy. Change the choices above until this paragraph feels comfortable to read for a long time.":
        "Basahin ang talata sa ibaba at sagutin ang mga tanong pagkatapos nito. Madaling tingnan sa mata ang magandang babasahin: sapat ang laki ng mga letra, hindi siksik ang mga linya, at maayos ang mga gilid. Baguhin ang mga pinili sa itaas hanggang maging komportable ang pagbasa ng talatang ito nang matagal.",
    "Text size": "Laki ng text",
    "Small": "Maliit",
    "Normal": "Normal",
    "Large": "Malaki",
    "Extra large": "Napakalaki",
    "Text alignment": "Pagkakahanay ng text",
    "Left": "Kaliwa",
    "Justified": "Justified",
    "Line spacing": "Pagitan ng linya",
    "Relaxed": "Maluwag",
    "Go to MyGuro": "Pumunta sa MyGuro",
}

_PAGES = dict(TAGLISH)  # the student and shared sentences, before the other files are added

# The server's messages (error answers) are in their own file because there are so many.
from myguro.i18n.tl_messages import MESSAGES  # noqa: E402
from myguro.i18n.tl_teacher import TEACHER  # noqa: E402
from myguro.i18n.tl_admin import ADMIN  # noqa: E402

TAGLISH.update(MESSAGES)
TAGLISH.update(TEACHER)
TAGLISH.update(ADMIN)

# What a page's JavaScript needs: everything except the messages only the server says (they are not sent to the
# browser). A sentence both the server and a page use is in the other files too, so it is kept.
# Sentences from tl_messages.py that a page's JavaScript says as well (tests/test_i18n_coverage.py fails when a
# script uses a server-only sentence that is not listed here).
ALSO_IN_BROWSER = {
    "Choose a grade or section to change.", "Individual students", "Last name is required.", "Periods a week",
    "Subject", "Teacher", "Subject is required.", "Title is required.", "The chatbot is not available right now.",
    "Username must be 3 to 30 letters, numbers, dots, dashes or underscores, with no spaces.",
}
CLIENT_TEXT = {english: taglish for english, taglish in TAGLISH.items()
               if english not in MESSAGES or english in ALSO_IN_BROWSER or english in TEACHER or english in ADMIN
               or english in _PAGES}
