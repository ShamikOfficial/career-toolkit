import unittest

from agent.browser.page_snapshot import ButtonSchema, FieldSchema, FormSchema


class TestFormSchemaDict(unittest.TestCase):
    def test_to_dict_shape(self):
        schema = FormSchema(
            url="https://example.com",
            title="Example",
            fields=[
                FieldSchema(
                    field_id="email",
                    selector="input[name=\"email\"]",
                    tag="input",
                    input_type="text",
                    label="Email",
                    placeholder="",
                    required=True,
                    options=None,
                )
            ],
            buttons=[ButtonSchema(selector="button[type=submit]", text="Submit", kind="submit")],
            errors=[],
        )
        d = schema.to_dict()
        self.assertIn("fields", d)
        self.assertEqual(d["fields"][0]["field_id"], "email")
        self.assertEqual(d["buttons"][0]["kind"], "submit")


if __name__ == "__main__":
    unittest.main()

