import tempfile
import unittest
from pathlib import Path

from agent.tools.drawio import upsert_drawio_diagram_executor


VALID_XML = """<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="n1" value="Start" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="40" y="40" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="n2" value="End" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="220" y="40" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="e1" edge="1" parent="1" source="n1" target="n2" style="edgeStyle=orthogonalEdgeStyle;html=1;">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
"""


class DrawioToolTests(unittest.TestCase):

    def test_create_valid_diagram(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = upsert_drawio_diagram_executor(
                workspace=workspace,
                diagram_path="diagrams/test.drawio",
                action="create",
                xml_content=VALID_XML,
                create_backup=False,
            )

            self.assertTrue(result.ok)
            self.assertTrue((workspace / "diagrams" / "test.drawio").exists())

    def test_reject_edge_without_required_geometry(self):
        invalid_xml = VALID_XML.replace(
            "<mxGeometry relative=\"1\" as=\"geometry\"/>",
            "",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = upsert_drawio_diagram_executor(
                workspace=workspace,
                diagram_path="diagram.drawio",
                action="create",
                xml_content=invalid_xml,
                create_backup=False,
            )

            self.assertFalse(result.ok)
            self.assertIn("Draw.io XML validation failed", result.error or "")
            self.assertIn("must contain <mxGeometry relative=\"1\" as=\"geometry\"/>", result.output or "")

    def test_reject_duplicate_ids(self):
        duplicate_xml = VALID_XML.replace('id="n2"', 'id="n1"', 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = upsert_drawio_diagram_executor(
                workspace=workspace,
                diagram_path="diagram.drawio",
                action="create",
                xml_content=duplicate_xml,
                create_backup=False,
            )

            self.assertFalse(result.ok)
            self.assertIn("duplicate id values", result.output or "")

    def test_update_creates_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "diagram.drawio"
            target.write_text(VALID_XML, encoding="utf-8")

            updated_xml = VALID_XML.replace("End", "Finish", 1)

            result = upsert_drawio_diagram_executor(
                workspace=workspace,
                diagram_path="diagram.drawio",
                action="update",
                xml_content=updated_xml,
                create_backup=True,
            )

            self.assertTrue(result.ok)
            backup_file = result.metadata.get("backup_file")
            self.assertIsNotNone(backup_file)
            self.assertTrue(Path(backup_file).exists())


if __name__ == "__main__":
    unittest.main()
