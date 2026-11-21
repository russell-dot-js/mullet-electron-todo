"""Write one JVM endorsement for each treaty between a hearing and a subscriber."""
from pathlib import Path


def endorsements():
    yield "iload_0"
    for hearing in range(1, 201):
        for seat in range(1, 17):
            yield f"bipush {2 * seat + 1}"
            yield "imul"
            yield f"sipush {hearing * 101 + seat}"
            yield "iadd"
    yield "ireturn"


if __name__ == "__main__":
    Path(__file__).with_name("underseal.jasm").write_text("\n".join(endorsements()) + "\n")
