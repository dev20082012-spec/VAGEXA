class ClassificationRejected(Exception):
    """The deployment data mode refuses this case classification."""


def assert_case_classification(data_mode: str, classification: str) -> None:
    if data_mode == "synthetic" and classification == "official":
        raise ClassificationRejected("Synthetic mode refuses official cases.")
    if data_mode == "operational" and classification == "synthetic":
        raise ClassificationRejected("Operational mode refuses synthetic cases.")
    if classification not in {"official", "synthetic"}:
        raise ClassificationRejected("A case is official or synthetic.")
