from sqlalchemy.orm import Session


class DocumentValidateService:
    def __init__(self, database):
        self.database = database
