import pytest

from bot.domain.services.dev_list import DevListService


class TestIsDev:
    @pytest.mark.anyio
    async def test_matches_a_whatsapp_dev_by_number_under_either_suffix(
        self, mock_mongodb_collection
    ):
        collection = mock_mongodb_collection('dev_list')
        collection.find_one.return_value = {'_id': '5511999999999@s.whatsapp.net'}

        is_dev = await DevListService().is_dev('5511999999999@lid')

        assert is_dev is True
        collection.find_one.assert_awaited_once_with(
            {'_id': {'$in': ['5511999999999@lid', '5511999999999@s.whatsapp.net']}}
        )

    @pytest.mark.anyio
    async def test_matches_a_namespaced_key_only_by_itself(self, mock_mongodb_collection):
        collection = mock_mongodb_collection('dev_list')
        collection.find_one.return_value = None

        is_dev = await DevListService().is_dev('telegram:5511999999999')

        assert is_dev is False
        collection.find_one.assert_awaited_once_with({'_id': {'$in': ['telegram:5511999999999']}})
