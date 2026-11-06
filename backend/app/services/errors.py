"""Framework-free exceptions raised by the service layer."""


class DatasetNotFoundError(KeyError):
    """Raised when a dataset id does not exist. A dedicated type (instead of a bare KeyError)
    stops unrelated KeyErrors from being reported to clients as '404 dataset not found'."""

    def __init__(self, dataset_id: str = ""):
        super().__init__(f"Dataset {dataset_id} not found.")
        self.dataset_id = dataset_id


class IngestError(ValueError):
    """The uploaded file cannot be turned into a dataset. `message` is shown to the user."""

    def __init__(self, message: str, code: str = "invalid_dataset"):
        super().__init__(message)
        self.message = message
        self.code = code
