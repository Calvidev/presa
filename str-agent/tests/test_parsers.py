"""Unit tests for the pure parsing helpers in each scraper (no network)."""
import datetime
import pytest

from str_agent.scrapers.airbnb import (
    _parse_stays_search_ids,
    _parse_calendar_months,
    _parse_price,
)
from str_agent.scrapers.booking import _parse_search_ids as booking_ids, _parse_calendar as booking_cal
from str_agent.scrapers.vrbo import _parse_search_ids as vrbo_ids, _parse_calendar as vrbo_cal


# ------------------------------------------------------------------ #
#  Airbnb                                                              #
# ------------------------------------------------------------------ #

def test_airbnb_parse_stays_search_ids():
    body = {
        "data": {
            "presentation": {
                "staysSearch": {
                    "results": {
                        "searchResults": [
                            {"listing": {"id": "123"}},
                            {"listing": {"id": "456"}},
                            {"other": "no listing key"},
                        ]
                    }
                }
            }
        }
    }
    assert _parse_stays_search_ids(body) == ["123", "456"]


def test_airbnb_parse_stays_search_ids_malformed():
    assert _parse_stays_search_ids({}) == []
    assert _parse_stays_search_ids({"data": None}) == []


def test_airbnb_parse_calendar_months():
    months = [
        {
            "weeks": [
                {
                    "days": [
                        {
                            "calendarDate": "2026-06-01",
                            "available": True,
                            "price": {"localPriceFormatted": "$120"},
                            "minNights": 2,
                        },
                        {
                            "calendarDate": "2026-06-02",
                            "available": False,
                            "price": {"localPriceFormatted": "$150"},
                        },
                    ]
                }
            ]
        }
    ]
    days = _parse_calendar_months(months)
    assert len(days) == 2
    assert days[0].date == datetime.date(2026, 6, 1)
    assert days[0].available is True
    assert days[0].price_usd == 120.0
    assert days[0].min_nights == 2
    assert days[1].available is False
    assert days[1].price_usd == 150.0


def test_airbnb_parse_price():
    assert _parse_price("$1,200") == 1200.0
    assert _parse_price("€99") == 99.0
    assert _parse_price("") is None
    assert _parse_price("N/A") is None


# ------------------------------------------------------------------ #
#  Booking.com                                                         #
# ------------------------------------------------------------------ #

def test_booking_parse_search_ids():
    data = {
        "data": {
            "searchQueries": {
                "search": {
                    "results": [
                        {"basicPropertyData": {"id": 1001}},
                        {"basicPropertyData": {"id": 1002}},
                    ]
                }
            }
        }
    }
    assert booking_ids(data) == ["1001", "1002"]


def test_booking_parse_search_ids_empty():
    assert booking_ids({}) == []


def test_booking_parse_calendar():
    data = {
        "data": {
            "property": {
                "availabilityCalendar": {
                    "days": [
                        {"date": "2026-06-01", "available": True,  "price": {"amount": 110.0}, "minLengthOfStay": 1},
                        {"date": "2026-06-02", "available": False, "price": {"amount": 130.0}},
                    ]
                }
            }
        }
    }
    days = booking_cal(data)
    assert len(days) == 2
    assert days[0].date == datetime.date(2026, 6, 1)
    assert days[0].available is True
    assert days[0].price_usd == 110.0
    assert days[1].available is False


# ------------------------------------------------------------------ #
#  VRBO                                                                #
# ------------------------------------------------------------------ #

def test_vrbo_parse_search_ids():
    body = {"propertyResults": [
        {"propertyId": "777"},
        {"propertyId": "888"},
    ]}
    assert vrbo_ids(body) == ["777", "888"]


def test_vrbo_parse_search_ids_fallback():
    body = {"results": [{"id": "999"}]}
    assert vrbo_ids(body) == ["999"]


def test_vrbo_parse_calendar():
    avail = [
        {"date": "2026-06-01", "available": True,  "amount": 200.0},
        {"date": "2026-06-02", "available": False, "amount": None},
    ]
    days = vrbo_cal(avail)
    assert len(days) == 2
    assert days[0].available is True
    assert days[0].price_usd == 200.0
    assert days[1].available is False


def test_vrbo_parse_calendar_bad_date():
    avail = [{"date": "not-a-date", "available": True}]
    days = vrbo_cal(avail)
    assert days == []
