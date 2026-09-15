from ovadue.applog import LOG_FILENAME, configure_logging, get_logger


def test_configure_logging_writes_rotating_file(tmp_path) -> None:
    logger = configure_logging(tmp_path)
    logger.info("hello-ovadue")
    for handler in logger.handlers:
        handler.flush()
    log_file = tmp_path / "data" / LOG_FILENAME
    assert log_file.exists()
    assert "hello-ovadue" in log_file.read_text(encoding="utf-8")
    assert get_logger() is logger
