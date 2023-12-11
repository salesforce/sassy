import unittest
import json

from sassy.data_model.oas import OpenAPI
from sassy.main import render_openapi


class TestParsingOpenAPISPec(unittest.TestCase):

    def test_parsing(self):
        spec_str = json.loads(render_openapi())
        spec = OpenAPI(**spec_str)

        self.assertEqual(spec.openapi, '3.0.3')

        path = spec.paths['/data/v59.0/sobjects/{sObject}'].get
        assert path is not None
        self.assertEqual(path.operation_id, 'getObjectMetadata')


if __name__ == '__main__':
    unittest.main()
