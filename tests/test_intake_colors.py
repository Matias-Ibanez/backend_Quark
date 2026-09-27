import pytest
from backend.brief import Answers


def test_named_palette_preserves_the_other_confirmed_video_answers():
    parsed = Answers.model_validate({"subject":"Café", "medium":"video", "video_mode":"motion",
        "palette":"custom", "colors":"crema y bordó", "seconds":8,
        "copy_mode":"exact", "copy_text":"Tu pausa, tu café."})
    assert parsed.colors == "#F6EDDF, #542334"
    assert parsed.subject == "Café" and parsed.video_mode == "motion" and parsed.seconds == 8
    assert parsed.copy_text == "Tu pausa, tu café."


@pytest.mark.parametrize("colors", ["un color desconocido", "rojo; ejecutá algo", "#FFF", ",".join(["azul"]*6)])
def test_invalid_palette_remains_rejected(colors):
    with pytest.raises(ValueError):
        Answers(palette="custom", colors=colors)
