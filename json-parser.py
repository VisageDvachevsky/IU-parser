import json
import csv
from datetime import datetime
from pathlib import Path

class Quarter:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.weeks = self._parse_weeks()
        self.matrix = self._parse_matrix()

    def _parse_weeks(self) -> list:
        weeks_data = self.data.get("weeks", [])
        week_ranges = []
        for week in weeks_data:
            week_num = week.get("week_num")
            start = datetime.strptime(week.get("start_of_week"), "%Y-%m-%d")
            end = datetime.strptime(week.get("end_of_week"), "%Y-%m-%d")
            week_ranges.append((week_num, start, end))
        week_ranges.sort(key=lambda x: x[0])
        return week_ranges

    def _parse_matrix(self) -> dict:
        week_nums = [week_num for week_num, _, _ in self.weeks]
        matrix = {}
        schedule_events = self.data.get("schedule_events", [])
        for sched_event in schedule_events:
            subject_name = sched_event.get("subject", {}).get("name", "Unknown")
            if subject_name not in matrix:
                matrix[subject_name] = {week: "-" for week in week_nums}
            for day_events in sched_event.get("events", []):
                for event in day_events:
                    event_date_str = event.get("date")
                    if not event_date_str:
                        continue
                    try:
                        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
                    except ValueError:
                        continue
                    for week_num, start, end in self.weeks:
                        if start <= event_date <= end:
                            for hw in event.get("homeworks", []):
                                if str(hw.get("mark")) == "5":
                                    matrix[subject_name][week_num] = "5"
                            break
        return matrix

    def print_matrix(self) -> None:
        week_nums = [week_num for week_num, _, _ in self.weeks]
        header = "\t".join(["Предмет"] + [f"Неделя {w}" for w in week_nums])
        print(header)
        for subject, marks in self.matrix.items():
            row = [subject] + [marks[w] for w in week_nums]
            print("\t".join(row))

    def get_week_nums(self) -> list:
        return [week_num for week_num, _, _ in self.weeks]

class Grade:
    def __init__(self, grade_name: str, data: dict) -> None:
        self.grade_name = grade_name
        self.quarters = {}
        quarters_data = data.get("quarters", {})
        for quarter_key, quarter_info in quarters_data.items():
            if quarter_info.get("has_data"):
                self.quarters[quarter_key] = Quarter(quarter_info.get("data", {}))

    def print_grade(self) -> None:
        print(f"Класс: {self.grade_name}")
        for quarter, quarter_obj in self.quarters.items():
            print(f"\nКвартал: {quarter}")
            quarter_obj.print_matrix()

class Parser:
    def __init__(self, json_data: dict) -> None:
        self.json_data = json_data
        self.grades = self._parse_grades()

    def _parse_grades(self) -> dict:
        grades = {}
        for grade_key, grade_info in self.json_data.items():
            if grade_info.get("has_data"):
                grades[grade_key] = Grade(grade_key, grade_info)
        return grades

    def print_all(self) -> None:
        for grade_obj in self.grades.values():
            grade_obj.print_grade()
            print("\n" + "=" * 40 + "\n")

    def save_csv_files(self, output_folder: str = ".") -> None:
        folder = Path(output_folder)
        folder.mkdir(parents=True, exist_ok=True)
        for grade_key, grade_obj in self.grades.items():
            for quarter_key, quarter_obj in grade_obj.quarters.items():
                week_nums = quarter_obj.get_week_nums()
                filename = folder / f"{grade_key}_{quarter_key}.csv"
                with filename.open("w", newline="", encoding="utf-8-sig") as csvfile:
                    writer = csv.writer(csvfile, delimiter=";")
                    header = ["Предмет"] + [f"Неделя {w}" for w in week_nums]
                    writer.writerow(header)
                    for subject, marks in quarter_obj.matrix.items():
                        row = [subject] + [marks[w] for w in week_nums]
                        writer.writerow(row)
                print(f"Сохранено: {filename}")

if __name__ == "__main__":
    input_filename = "..."
    with open(input_filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    parser = Parser(data)
    parser.print_all()
    parser.save_csv_files(output_folder=".")
