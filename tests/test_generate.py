"""Unit tests for the message generator."""
import sys
import os
import types
from unittest.mock import MagicMock, patch

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _make_mock_response(content: str):
    """Build a mock that matches openai.chat.completions.create() return shape."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


SAMPLE_PROFILE = {
    "name": "Jane Chen",
    "headline": "HR Manager at TechCorp",
    "company": "TechCorp",
    "location": "Taipei, Taiwan",
    "about": "Passionate about talent acquisition and building great teams.",
    "experiences": [
        {"title": "HR Manager", "company": "TechCorp", "dates": "2022 - Present"},
        {"title": "Recruiter", "company": "StartupXYZ", "dates": "2020 - 2022"},
    ],
}


def test_generate_message_returns_string():
    """generate_message should return a non-empty string."""
    mock_content = "TechCorp 的人才招募是否有在尋找新工具來提升效率？"
    with patch("generator.generate.openai.chat.completions.create") as mock_create:
        mock_create.return_value = _make_mock_response(mock_content)
        from generator.generate import generate_message
        result = generate_message(SAMPLE_PROFILE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_message_max_300_chars():
    """Output must be ≤300 characters."""
    short_content = "Hi Jane, how is recruiting going at TechCorp? Are you open to new sourcing tools?"
    with patch("generator.generate.openai.chat.completions.create") as mock_create:
        mock_create.return_value = _make_mock_response(short_content)
        from generator.generate import generate_message
        result = generate_message(SAMPLE_PROFILE)
    assert len(result) <= 300, f"Message too long: {len(result)} chars"


def test_generate_message_truncates_overlong():
    """If GPT returns >300 chars, output must still be ≤300."""
    long_content = "A" * 400
    with patch("generator.generate.openai.chat.completions.create") as mock_create:
        mock_create.return_value = _make_mock_response(long_content)
        from generator.generate import generate_message
        result = generate_message(SAMPLE_PROFILE)
    assert len(result) <= 300


def test_generate_message_retries_on_error():
    """On first API failure, it should retry once and succeed."""
    import openai
    mock_content = "Test message — are you exploring new HR tools at TechCorp?"
    with patch("generator.generate.openai.chat.completions.create") as mock_create:
        mock_create.side_effect = [
            openai.APIConnectionError(request=MagicMock()),
            _make_mock_response(mock_content),
        ]
        from generator.generate import generate_message
        result = generate_message(SAMPLE_PROFILE)
    assert result == mock_content
    assert mock_create.call_count == 2


def test_generate_message_raises_after_two_failures():
    """After two consecutive failures, an exception must propagate."""
    import openai
    import pytest
    with patch("generator.generate.openai.chat.completions.create") as mock_create:
        mock_create.side_effect = openai.APIConnectionError(request=MagicMock())
        from generator.generate import generate_message
        with pytest.raises(openai.OpenAIError):
            generate_message(SAMPLE_PROFILE)
