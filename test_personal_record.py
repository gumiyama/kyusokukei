import os
import json
import unittest

from personal_record import update_personal_record

class TestPersonalRecord(unittest.TestCase):
    def setUp(self):
        self.temp_file = 'tmp_records.json'
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_new_record(self):
        best, new = update_personal_record('Alice', 100.0, self.temp_file)
        self.assertTrue(new)
        self.assertEqual(best, 100.0)
        with open(self.temp_file) as f:
            data = json.load(f)
        self.assertEqual(data['Alice'], 100.0)

    def test_existing_record(self):
        update_personal_record('Bob', 90.0, self.temp_file)
        best, new = update_personal_record('Bob', 85.0, self.temp_file)
        self.assertFalse(new)
        self.assertEqual(best, 90.0)

if __name__ == '__main__':
    unittest.main()
