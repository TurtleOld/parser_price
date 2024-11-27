class DictionaryParser:
    def __init__(self, data):
        self.data = data

    def find_key(self, target_key):
        results = []
        self._search(self.data, target_key, results)
        return results

    def _search(self, current_dict, target_key, results):
        if isinstance(current_dict, dict):
            for key, value in current_dict.items():
                if key == target_key:
                    results.append(value)
                self._search(value, target_key, results)
        elif isinstance(current_dict, list):
            for item in current_dict:
                self._search(item, target_key, results)
