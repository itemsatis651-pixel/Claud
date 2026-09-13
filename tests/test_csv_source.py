import pytest

from src.data.csv_source import CsvUrlDataClient

COLUMN_MAP = {
    "timestamp": "UNIX_TIMESTAMP",
    "open": "OPEN",
    "high": "HIGH",
    "low": "LOW",
    "close": "CLOSE",
    "volume": "VOLUME_BTC",
}


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, text):
        self._text = text
        self.requested_urls = []

    def get(self, url, timeout=None):
        self.requested_urls.append(url)
        return FakeResponse(self._text)


CSV_TEXT = (
    "UNIX_TIMESTAMP,DATETIME,OPEN,HIGH,CLOSE,LOW,VOLUME_USD,VOLUME_BTC\n"
    "0,1970-01-01 00:00:00,100,110,105,90,1000,10\n"
    "3600,1970-01-01 01:00:00,105,115,108,95,1100,11\n"
    "7200,1970-01-01 02:00:00,108,120,112,100,1200,12\n"
)


def test_fetch_ohlcv_history_parses_and_filters_by_since_ms():
    client = CsvUrlDataClient(url="https://example.com/x.csv", column_map=COLUMN_MAP, session=FakeSession(CSV_TEXT))

    result = client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=3600 * 1000)

    assert [row[0] for row in result] == [3600 * 1000, 7200 * 1000]
    # sütun eşleme doğru mu: open, high, low, close, volume
    assert result[0][1:] == [105.0, 115.0, 95.0, 108.0, 11.0]


def test_fetch_ohlcv_history_filters_by_until_ms():
    client = CsvUrlDataClient(url="https://example.com/x.csv", column_map=COLUMN_MAP, session=FakeSession(CSV_TEXT))

    result = client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0, until_ms=3600 * 1000)

    assert [row[0] for row in result] == [0]


def test_load_is_cached_across_calls():
    session = FakeSession(CSV_TEXT)
    client = CsvUrlDataClient(url="https://example.com/x.csv", column_map=COLUMN_MAP, session=session)

    client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0)
    client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0)

    assert len(session.requested_urls) == 1


def test_missing_column_raises_value_error():
    bad_csv = "UNIX_TIMESTAMP,OPEN\n0,100\n"
    client = CsvUrlDataClient(url="https://example.com/x.csv", column_map=COLUMN_MAP, session=FakeSession(bad_csv))

    with pytest.raises(ValueError):
        client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0)


def test_column_map_missing_required_key_raises():
    with pytest.raises(ValueError):
        CsvUrlDataClient(url="https://example.com/x.csv", column_map={"timestamp": "T"})
