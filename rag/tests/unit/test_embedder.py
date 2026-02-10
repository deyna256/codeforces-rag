from unittest.mock import MagicMock

from src.embedder import BATCH_SIZE, embed_texts


class TestEmbedTexts:
    def test_single_batch_calls_api_once(self, mock_openai_client):
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        )

        result = embed_texts(["hello"])

        assert result == [[0.1, 0.2, 0.3]]
        mock_openai_client.embeddings.create.assert_called_once()

    def test_multiple_batches_calls_api_per_batch(self, mock_openai_client):
        first_batch = MagicMock(
            data=[MagicMock(embedding=[0.1])] * BATCH_SIZE
        )
        second_batch = MagicMock(
            data=[MagicMock(embedding=[0.2])]
        )
        mock_openai_client.embeddings.create.side_effect = [first_batch, second_batch]

        result = embed_texts(["text"] * (BATCH_SIZE + 1))

        assert mock_openai_client.embeddings.create.call_count == 2
        assert len(result) == BATCH_SIZE + 1

    def test_preserves_embedding_order(self, mock_openai_client):
        expected = [[0.1], [0.2], [0.3]]
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=e) for e in expected]
        )

        result = embed_texts(["a", "b", "c"])

        assert result == expected
