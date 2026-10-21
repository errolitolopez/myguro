"""The seed-demo command: a sample class with answers, scores and remarks."""

from conftest import login


def test_seed_demo_adds_the_class_once(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-demo"])
    assert result.exit_code == 0, result.output
    assert "Added the class Grade 9 - Rizal" in result.output

    teacher = login("ecruz")
    assert [item["name"] for item in teacher.get("/api/classes").get_json()["classes"]] == ["Grade 9 - Rizal"]
    assert "already has" in runner.invoke(args=["seed-demo"]).output
