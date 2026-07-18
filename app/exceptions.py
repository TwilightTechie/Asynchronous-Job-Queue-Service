from uuid import UUID


class JobNotFoundError(Exception):
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id
        super().__init__(f"No job with id {job_id}")
