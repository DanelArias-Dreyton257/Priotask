class TaskDTO:
    def __init__(self, name, deadline, expected_duration, importance):
        self.name = name
        self.deadline = deadline
        self.expected_duration = expected_duration
        self.importance = importance

    def __repr__(self):
        return f"TaskDTO(name={self.name}, deadline={self.deadline}, expected_duration={self.expected_duration}, importance={self.importance})"
