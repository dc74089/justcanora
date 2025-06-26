from django.conf import settings

from aitutor.models import Agent


def construct_agents():
    base_py = ""
    base_java = ""

    dir = settings.BASE_DIR / "aitutor/agents"

    with open(dir / "base-java.txt", "r") as f:
        base_java = f.read()

    with open(dir / "base-python.txt", "r") as f:
        base_py = f.read()

    for file in dir.glob("*"):
        if file.is_file() and not file.name.startswith("base-"):
            with open(file, "r") as f:
                flavor = f.read()

                java_agent, _ = Agent.objects.get_or_create(name=file.name.removesuffix(".txt"), language="java")
                java_agent.dev_message = flavor.replace("-----", base_java)
                java_agent.save()

                python_agent, _ = Agent.objects.get_or_create(name=file.name.removesuffix(".txt"), language="python")
                python_agent.dev_message = flavor.replace("-----", base_py)
                python_agent.save()

    with open(dir / "assessment" / "base.txt", "r") as f:
        base_assessment = f.read()

        assessment_agent = Agent.get_assessment_agent()
        assessment_agent.dev_message = base_assessment
        assessment_agent.save()