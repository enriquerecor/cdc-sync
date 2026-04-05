from kafka.structs import OffsetAndMetadata, TopicPartition

from offset_commit_tracker import OffsetCommitTracker


def test_build_commit_offsets_returns_next_offset_for_contiguous_records() -> None:
    tracker = OffsetCommitTracker()

    tracker.mark_processed("cdc_sync.public.customers", 0, 10)
    tracker.mark_processed("cdc_sync.public.customers", 0, 11)

    assert tracker.build_commit_offsets() == {
        TopicPartition("cdc_sync.public.customers", 0): OffsetAndMetadata(
            offset=12,
            metadata=None,
            leader_epoch=-1,
        )
    }


def test_build_commit_offsets_keeps_gap_until_missing_offset_is_processed() -> None:
    tracker = OffsetCommitTracker()

    tracker.mark_processed("cdc_sync.public.customers", 0, 10)
    tracker.mark_processed("cdc_sync.public.customers", 0, 12)

    assert tracker.build_commit_offsets() == {
        TopicPartition("cdc_sync.public.customers", 0): OffsetAndMetadata(
            offset=11,
            metadata=None,
            leader_epoch=-1,
        )
    }

    tracker.mark_committed(tracker.build_commit_offsets())
    tracker.mark_processed("cdc_sync.public.customers", 0, 11)

    assert tracker.build_commit_offsets() == {
        TopicPartition("cdc_sync.public.customers", 0): OffsetAndMetadata(
            offset=13,
            metadata=None,
            leader_epoch=-1,
        )
    }


def test_mark_committed_removes_offsets_already_confirmed() -> None:
    tracker = OffsetCommitTracker()

    tracker.mark_processed("cdc_sync.public.customers", 0, 20)
    tracker.mark_processed("cdc_sync.public.customers", 0, 21)

    commit_offsets = tracker.build_commit_offsets()
    tracker.mark_committed(commit_offsets)

    assert tracker.partition_states == {
        TopicPartition("cdc_sync.public.customers", 0): tracker.partition_states[
            TopicPartition("cdc_sync.public.customers", 0)
        ]
    }
    assert tracker.partition_states[
        TopicPartition("cdc_sync.public.customers", 0)
    ].next_commit_offset == 22
    assert (
        tracker.partition_states[
            TopicPartition("cdc_sync.public.customers", 0)
        ].processed_offsets
        == set()
    )
