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
}
