import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from dotenv import load_dotenv
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()

DB_URL = os.getenv("DB_URI")
if not DB_URL:
    raise RuntimeError("DB_URI non trovata. Impostala nel file .env.")

XLSX_PATH = Path("Ark Nova abilities.xlsx")

engine = create_engine(DB_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Ability(Base):
    __tablename__ = "abilities"

    ability_name = Column(String, primary_key=True)
    normalized_name = Column(String, unique=True, nullable=False, index=True)
    effect = Column(String)
    expansion = Column(String)


def normalize_ability_name(value: str) -> str:
    value = re.sub(r"\s*:\s*", ": ", value.strip())
    value = re.sub(r"\s+", " ", value)
    return value.lower()


def _cell_text(cell, shared_strings, namespace):
    value_node = cell.find("a:v", namespace)
    if value_node is None:
        inline_text = cell.find(".//a:t", namespace)
        return "" if inline_text is None else inline_text.text or ""

    value = value_node.text or ""
    if cell.attrib.get("t") == "s" and value:
        return shared_strings[int(value)]
    return value


def read_abilities_xlsx(path: Path):
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    with ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall("a:si", namespace):
                shared_strings.append(
                    "".join(text.text or "" for text in item.findall(".//a:t", namespace))
                )

        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = sheet_root.findall("a:sheetData/a:row", namespace)

        for row in rows[1:]:
            values = {}
            for cell in row.findall("a:c", namespace):
                column = re.sub(r"\d+", "", cell.attrib["r"])
                values[column] = _cell_text(cell, shared_strings, namespace).strip()

            ability_name = values.get("A", "")
            if not ability_name:
                continue

            yield {
                "ability_name": ability_name,
                "normalized_name": normalize_ability_name(ability_name),
                "effect": values.get("B") or None,
                "expansion": values.get("C") or None,
            }


def ingest_abilities():
    Base.metadata.create_all(engine)

    with Session() as session:
        count = 0
        for entry in read_abilities_xlsx(XLSX_PATH):
            session.merge(Ability(**entry))
            count += 1
        session.commit()

    print(f"Ingestione di {count} abilita completata.")


if __name__ == "__main__":
    ingest_abilities()
