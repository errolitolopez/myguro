"""Building a weekly timetable: the rules, the search, and a checker that lists broken rules.

No Flask and no SQL: it gets plain lists and dicts and returns plain lists and dicts.

A slot is (section_id, day, period, subject, teacher_id); days are 0 = Monday ... 4 = Friday and periods are
0, 1, 2 ... in the order of the school day (the health break is not a period).
"""

import math
import random

DAYS = 5
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
# The teaching periods of a school day. The health break after the third one is not a period.
PERIOD_TIMES = (("6:00", "6:50"), ("6:50", "7:40"), ("7:40", "8:30"), ("8:45", "9:35"), ("9:35", "10:25"),
                ("10:25", "11:15"))
BREAK_AFTER = 2  # the index of the period the health break follows

# What the generator is told when the admin has not changed anything.
DEFAULT_RULES = {
    "max_gap": 2,           # longest idle stretch (in periods) a teacher may have between two classes of a day
    "max_per_day": None,    # most periods a teacher teaches in a day; None = every period of the day
    "max_subject_per_day": 2,  # most periods of one subject a section has in a day
}

# How much each avoided thing costs. A smaller total is a better timetable.
LONG_GAP_PENALTY = 1000   # per idle period beyond max_gap
GAP_PENALTY = 10          # per idle period between a teacher's classes
HOLE_PENALTY = 60         # per free period in a section's day that has a lesson after it
TOO_MANY_PENALTY = 500    # per period over max_subject_per_day
SPLIT_PENALTY = 40        # a subject twice in one day, but not back to back
SPREAD_PENALTY = 25       # per day a subject could use but does not


def check_inputs(assignments, teachers, periods):
    """Problems that make a timetable impossible whatever the search does (a list of sentences)."""
    problems = []
    per_section, per_teacher = {}, {}
    for item in assignments:
        per_section[item["section_id"]] = per_section.get(item["section_id"], 0) + item["per_week"]
        per_teacher[item["teacher_id"]] = per_teacher.get(item["teacher_id"], 0) + item["per_week"]
    for section_id, total in per_section.items():
        if total > DAYS * periods:
            problems.append({"kind": "section_full", "section_id": section_id,
                             "message": f"A section has {total} periods a week but only {DAYS * periods} fit."})
    for teacher_id, total in per_teacher.items():
        info = teachers.get(teacher_id, {})
        room = DAYS * periods - len(info.get("blocked", ()))
        if total > room:
            problems.append({"kind": "teacher_full", "teacher_id": teacher_id,
                             "message": f"A teacher has {total} periods a week to teach but only {room} are open."})
    return problems


class Timetable:
    """The working state of one search: who is where, and what it costs."""

    def __init__(self, assignments, teachers, periods, rules):
        self.periods = periods
        self.rules = {**DEFAULT_RULES, **(rules or {})}
        self.teachers = teachers
        self.lessons = []  # (section_id, subject, teacher_id), one per period to place
        self.per_week = {}  # (section_id, subject) -> periods a week
        for item in assignments:
            for _ in range(item["per_week"]):
                self.lessons.append((item["section_id"], item["subject"], item["teacher_id"]))
            key = (item["section_id"], item["subject"])
            self.per_week[key] = self.per_week.get(key, 0) + item["per_week"]
        self.sections = sorted({lesson[0] for lesson in self.lessons})
        # grid[section][day][period] = lesson number or None
        self.grid = {s: [[None] * periods for _ in range(DAYS)] for s in self.sections}
        self.occupied = {}  # (teacher, day, period) -> how many sections the teacher is in (must stay <= 1)
        self.teacher_load = {}  # (teacher, day) -> periods taught that day

    # --- limits -------------------------------------------------------------------------------

    def max_per_day(self, teacher):
        own = self.teachers.get(teacher, {}).get("max_per_day")
        return own or self.rules["max_per_day"] or self.periods

    def max_gap(self, teacher):
        own = self.teachers.get(teacher, {}).get("max_gap")
        return self.rules["max_gap"] if own is None else own

    def blocked(self, teacher, day, period):
        return (day, period) in self.teachers.get(teacher, {}).get("blocked", ())

    def teacher_free(self, teacher, day, period):
        return not self.occupied.get((teacher, day, period)) and not self.blocked(teacher, day, period)

    # --- changing the state ---------------------------------------------------------------------

    def put(self, lesson, day, period):
        section, _, teacher = self.lessons[lesson]
        self.grid[section][day][period] = lesson
        self.occupied[(teacher, day, period)] = self.occupied.get((teacher, day, period), 0) + 1
        self.teacher_load[(teacher, day)] = self.teacher_load.get((teacher, day), 0) + 1

    def take(self, lesson, day, period):
        section, _, teacher = self.lessons[lesson]
        self.grid[section][day][period] = None
        self.occupied[(teacher, day, period)] -= 1
        self.teacher_load[(teacher, day)] -= 1

    # --- costs (each one looks at a single teacher-day, section-day or section-subject) ---------------

    def teacher_day_cost(self, teacher, day):
        taught = [p for p in range(self.periods) if self.occupied.get((teacher, day, p))]
        if len(taught) < 2:
            return 0
        cost, longest, run = 0, 0, 0
        for before, after in zip(taught, taught[1:]):
            run = after - before - 1
            longest = max(longest, run)
            cost += run * GAP_PENALTY
        return cost + max(0, longest - self.max_gap(teacher)) * LONG_GAP_PENALTY

    def section_day_cost(self, section, day):
        row = self.grid[section][day]
        cost, free, counts, where = 0, 0, {}, {}
        for period, lesson in enumerate(row):
            if lesson is None:
                free += 1
                continue
            cost += free * HOLE_PENALTY  # every free period before this lesson is a hole
            free = 0
            subject = self.lessons[lesson][1]
            counts[subject] = counts.get(subject, 0) + 1
            where.setdefault(subject, []).append(period)
        limit = self.rules["max_subject_per_day"]
        for subject, count in counts.items():
            if count > limit:
                cost += (count - limit) * TOO_MANY_PENALTY
            elif count == 2 and where[subject][1] - where[subject][0] != 1:
                cost += SPLIT_PENALTY
        return cost

    def section_subject_cost(self, section, subject):
        days = sum(1 for day in range(DAYS)
                   if any(lesson is not None and self.lessons[lesson][1] == subject for lesson in self.grid[section][day]))
        return max(0, min(self.per_week[(section, subject)], DAYS) - days) * SPREAD_PENALTY

    def total_cost(self):
        cost = 0
        teachers = {lesson[2] for lesson in self.lessons}
        for teacher in teachers:
            cost += sum(self.teacher_day_cost(teacher, day) for day in range(DAYS))
        for section in self.sections:
            cost += sum(self.section_day_cost(section, day) for day in range(DAYS))
        for (section, subject) in self.per_week:
            cost += self.section_subject_cost(section, subject)
        return cost

    def local_cost(self, keys):
        total = 0
        for key in keys:
            if key[0] == "t":
                total += self.teacher_day_cost(key[1], key[2])
            elif key[0] == "d":
                total += self.section_day_cost(key[1], key[2])
            else:
                total += self.section_subject_cost(key[1], key[2])
        return total

    # --- building ---------------------------------------------------------------------------------

    def can_place(self, lesson, day, period):
        section, subject, teacher = self.lessons[lesson]
        if self.grid[section][day][period] is not None or not self.teacher_free(teacher, day, period):
            return False
        if self.teacher_load.get((teacher, day), 0) >= self.max_per_day(teacher):
            return False
        same = sum(1 for other in self.grid[section][day] if other is not None and self.lessons[other][1] == subject)
        return same < self.rules["max_subject_per_day"]

    def place_greedily(self, rng):
        """Put every lesson in the best free slot it can have right now. Returns the lessons left over."""
        load = {}
        for _, _, teacher in self.lessons:
            load[teacher] = load.get(teacher, 0) + 1
        order = sorted(range(len(self.lessons)), key=lambda n: (-load[self.lessons[n][2]], rng.random()))
        left = []
        for lesson in order:
            section, subject, teacher = self.lessons[lesson]
            best, best_score = None, None
            for day in range(DAYS):
                same_today = sum(1 for o in self.grid[section][day] if o is not None and self.lessons[o][1] == subject)
                filled = sum(1 for o in self.grid[section][day] if o is not None)
                for period in range(self.periods):
                    if not self.can_place(lesson, day, period):
                        continue
                    score = same_today * 30 + abs(period - filled) * 12  # fill the day from the top, spread subjects
                    taught = [p for p in range(self.periods) if self.occupied.get((teacher, day, p))]
                    if taught:  # stay close to the teacher's other classes that day
                        score += max(0, min(abs(period - p) for p in taught) - 1) * 15
                    score += rng.random() * 8
                    if best_score is None or score < best_score:
                        best, best_score = (day, period), score
            if best is None:
                left.append(lesson)
            else:
                self.put(lesson, *best)
        return left

    def improve(self, rng, steps):
        """Swap two periods of one section when that keeps every hard rule and lowers the cost
        (or, early on, sometimes when it raises it a little, to get out of dead ends)."""
        if not self.sections:
            return
        slots = [(d, p) for d in range(DAYS) for p in range(self.periods)]
        for step in range(steps):
            heat = 25 * (1 - step / steps) + 0.5
            section = rng.choice(self.sections)
            first, second = rng.sample(slots, 2)
            x, y = self.grid[section][first[0]][first[1]], self.grid[section][second[0]][second[1]]
            if x is None and y is None:
                continue
            moves = [(x, first, second), (y, second, first)]  # (lesson, where it is, where it goes)
            keys = {("d", section, first[0]), ("d", section, second[0])}
            for lesson, here, there in moves:
                if lesson is not None:
                    _, subject, teacher = self.lessons[lesson]
                    keys.update({("s", section, subject), ("t", teacher, here[0]), ("t", teacher, there[0])})
            before = self.local_cost(keys)
            for lesson, here, _ in moves:  # lift both out first, so they can take each other's place
                if lesson is not None:
                    self.take(lesson, *here)
            put = []
            for lesson, _, there in moves:
                if lesson is None:
                    continue
                teacher = self.lessons[lesson][2]
                if (not self.teacher_free(teacher, *there)
                        or self.teacher_load.get((teacher, there[0]), 0) >= self.max_per_day(teacher)):
                    break
                self.put(lesson, *there)
                put.append((lesson, there))
            else:
                delta = self.local_cost(keys) - before
                if delta <= 0 or rng.random() < math.exp(-delta / heat):
                    continue  # keep the swap
            for lesson, there in put:  # not allowed or not better: undo
                self.take(lesson, *there)
            for lesson, here, _ in moves:
                if lesson is not None:
                    self.put(lesson, *here)

    def slots(self):
        return [(section, day, period, self.lessons[lesson][1], self.lessons[lesson][2])
                for section in self.sections for day in range(DAYS) for period in range(self.periods)
                if (lesson := self.grid[section][day][period]) is not None]


def generate(assignments, teachers, periods, rules=None, seed=1, restarts=4, steps=20000):
    """Build a timetable.

    assignments: [{section_id, subject, teacher_id, per_week}]
    teachers: {teacher_id: {"blocked": {(day, period)}, "max_per_day": int or None, "max_gap": int or None}}
    periods: how many teaching periods a day has.
    Returns {"slots", "unplaced": [{section_id, subject, teacher_id}], "cost", "problems"}. The best of
    `restarts` tries is kept: the one that placed the most lessons, then the cheapest.
    """
    problems = check_inputs(assignments, teachers, periods)
    best = None
    for attempt in range(restarts):
        rng = random.Random(seed * 1000 + attempt)
        # The first placement is quick, so try again (up to 40 times) until every lesson has a slot
        table, left = None, None
        for _ in range(40):
            candidate = Timetable(assignments, teachers, periods, rules)
            candidate_left = candidate.place_greedily(rng)
            if left is None or len(candidate_left) < len(left):
                table, left = candidate, candidate_left
            if not left:
                break
        table.improve(rng, steps)
        result = (len(left), table.total_cost(), attempt, table, left)
        if best is None or result[:2] < best[:2]:
            best = result
        if not left and result[1] == 0:
            break
    _, cost, _, table, left = best
    return {
        "slots": table.slots(),
        "unplaced": [{"section_id": table.lessons[n][0], "subject": table.lessons[n][1],
                      "teacher_id": table.lessons[n][2]} for n in left],
        "cost": cost,
        "problems": problems,
    }


def check(slots, assignments, teachers, periods, rules=None):
    """The rules a timetable breaks, as a list of {kind, message, ...}: used after the admin swaps periods by hand.
    The same slots format as generate()."""
    table = Timetable(assignments, teachers, periods, rules)
    problems = []
    seen = {}
    for section, day, period, subject, teacher in slots:
        key = (teacher, day, period)
        if key in seen:
            problems.append({"kind": "teacher_double", "teacher_id": teacher, "day": day, "period": period,
                             "message": "A teacher is in two classes at the same time."})
        seen[key] = section
        if table.blocked(teacher, day, period):
            problems.append({"kind": "teacher_blocked", "teacher_id": teacher, "day": day, "period": period,
                             "message": "A teacher is placed in a period they cannot teach."})
    placed = {}
    by_teacher_day = {}
    by_section_day = {}
    for section, day, period, subject, teacher in slots:
        placed[(section, subject, teacher)] = placed.get((section, subject, teacher), 0) + 1
        by_teacher_day.setdefault((teacher, day), []).append(period)
        by_section_day.setdefault((section, day), []).append((period, subject))
    for item in assignments:
        have = placed.get((item["section_id"], item["subject"], item["teacher_id"]), 0)
        if have != item["per_week"]:
            problems.append({"kind": "wrong_count", "section_id": item["section_id"], "subject": item["subject"],
                             "message": f"{item['subject']} has {have} periods, it needs {item['per_week']}."})
    for (teacher, day), taught in by_teacher_day.items():
        taught.sort()
        if len(taught) > table.max_per_day(teacher):
            problems.append({"kind": "too_long_day", "teacher_id": teacher, "day": day,
                             "message": "A teacher teaches more periods in a day than allowed."})
        for before, after in zip(taught, taught[1:]):
            if after - before - 1 > table.max_gap(teacher):
                problems.append({"kind": "long_gap", "teacher_id": teacher, "day": day,
                                 "message": "A teacher has a long gap between two classes."})
    limit = table.rules["max_subject_per_day"]
    for (section, day), items in by_section_day.items():
        counts = {}
        for _, subject in items:
            counts[subject] = counts.get(subject, 0) + 1
        for subject, count in counts.items():
            if count > limit:
                problems.append({"kind": "too_many_subject", "section_id": section, "day": day, "subject": subject,
                                 "message": f"{subject} is more than {limit} times in one day."})
        periods_used = sorted(period for period, _ in items)
        if periods_used and periods_used != list(range(periods_used[0], periods_used[-1] + 1)):
            problems.append({"kind": "hole", "section_id": section, "day": day,
                             "message": "A section has a free period between two lessons."})
    return problems
