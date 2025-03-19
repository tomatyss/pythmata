"""Tests for timer parser module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

import sys
import importlib


def reload_timer_parser():
    # Clear timer_parser and its dependencies from sys.modules
    for module in list(sys.modules):
        if module.startswith("pythmata.core.engine.events.timer_parser"):
            del sys.modules[module]
    # Re-import the module to reset its state
    import pythmata.core.engine.events.timer_parser as timer_parser
    importlib.reload(timer_parser)
    return timer_parser


class TestTimerParser:
    """Test suite for timer parser functions."""

    def test_parse_duration(self):
        """Test parsing ISO 8601 duration strings."""

        timer_parser = reload_timer_parser()

        # Test valid durations
        assert timer_parser._parse_duration("PT1H") == timedelta(hours=1)
        assert timer_parser._parse_duration("PT30M") == timedelta(minutes=30)
        assert timer_parser._parse_duration("PT45S") == timedelta(seconds=45)
        assert timer_parser._parse_duration("PT1H30M") == timedelta(hours=1, minutes=30)
        assert timer_parser._parse_duration("PT1H30M45S") == timedelta(
            hours=1, minutes=30, seconds=45
        )

        # Test invalid durations
        assert timer_parser._parse_duration("1H") is None
        assert timer_parser._parse_duration("P1D") is None
        assert timer_parser._parse_duration("invalid") is None

    def test_parse_timer_definition_duration(self):
        """Test parsing duration timer definitions."""
        
        timer_parser = reload_timer_parser()

        # Setup mock datetime with context manager for better isolation
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch(
            "pythmata.core.engine.events.timer_parser.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.side_effect = datetime

            # Test duration timer
            timer_def = timer_parser.parse_timer_definition("PT1H")
            assert timer_def is not None
            assert timer_def.timer_type == "duration"
            assert isinstance(timer_def.trigger, DateTrigger)
            assert timer_def.duration == timedelta(hours=1)
            assert timer_def.trigger.run_date == now + timedelta(hours=1)

    def test_parse_timer_definition_cycle(self):
        """Test parsing cycle timer definitions."""

        timer_parser = reload_timer_parser()

        # Setup mock datetime with context manager for better isolation
        now2 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch(
            "pythmata.core.engine.events.timer_parser.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = now2

            # Test cycle timer
            timer_def = timer_parser.parse_timer_definition("R3/PT1H")
            assert timer_def is not None
            assert timer_def.timer_type == "cycle"
            assert isinstance(timer_def.trigger, IntervalTrigger)
            assert timer_def.repetitions == 3
            assert timer_def.interval == timedelta(hours=1)
            # The IntervalTrigger stores the interval as a timedelta object
            assert timer_def.trigger.interval == timedelta(hours=1)

    def test_parse_timer_definition_date(self):
        """Test parsing date timer definitions."""

        timer_parser = reload_timer_parser()

        # Test date timer
        date_str = "2025-01-01T12:00:00+00:00"
        timer_def = timer_parser.parse_timer_definition(date_str)
        assert timer_def is not None
        assert timer_def.timer_type == "date"
        assert isinstance(timer_def.trigger, DateTrigger)
        assert timer_def.target_date == datetime.fromisoformat(date_str)
        assert timer_def.trigger.run_date == datetime.fromisoformat(date_str)

    def test_extract_timer_definition(self):
        """Test extracting timer definitions from BPMN XML."""

        timer_parser = reload_timer_parser()

        # Simple BPMN XML with timer start event
        bpmn_xml = """
        <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
          <bpmn:process id="Process_1">
            <bpmn:startEvent id="StartEvent_1">
              <bpmn:timerEventDefinition id="TimerEventDefinition_1">
                <bpmn:timeDuration>PT1H</bpmn:timeDuration>
              </bpmn:timerEventDefinition>
            </bpmn:startEvent>
          </bpmn:process>
        </bpmn:definitions>
        """

        # Test extraction
        timer_def = timer_parser.extract_timer_definition(bpmn_xml, "StartEvent_1")
        assert timer_def == "PT1H"

        # Test non-existent node
        timer_def = timer_parser.extract_timer_definition(bpmn_xml, "NonExistentEvent")
        assert timer_def is None

        # Test non-timer event
        bpmn_xml_no_timer = """
        <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
          <bpmn:process id="Process_1">
            <bpmn:startEvent id="StartEvent_1">
            </bpmn:startEvent>
          </bpmn:process>
        </bpmn:definitions>
        """
        timer_def = timer_parser.extract_timer_definition(bpmn_xml_no_timer, "StartEvent_1")
        assert timer_def is None

    def test_find_timer_events_in_definition(self):
        """Test finding timer events in a process definition."""

        timer_parser = reload_timer_parser()

        # Simple BPMN XML with timer start event
        bpmn_xml = """
        <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
          <bpmn:process id="Process_1">
            <bpmn:startEvent id="StartEvent_1">
              <bpmn:timerEventDefinition id="TimerEventDefinition_1">
                <bpmn:timeDuration>PT1H</bpmn:timeDuration>
              </bpmn:timerEventDefinition>
            </bpmn:startEvent>
          </bpmn:process>
        </bpmn:definitions>
        """

        with patch(
            "pythmata.core.engine.events.timer_parser.extract_timer_definition"
        ) as mock_extract:
            # Setup mock
            mock_extract.return_value = "PT1H"

            # Test finding timer events
            timer_events = timer_parser.find_timer_events_in_definition(bpmn_xml, "prefix:", "def1")
            assert len(timer_events) == 1
            assert timer_events[0] == (
                "prefix:def1:StartEvent_1",
                "StartEvent_1",
                "PT1H",
            )
