from dataclasses import dataclass, field

from kafka.structs import OffsetAndMetadata, TopicPartition


@dataclass
class PartitionOffsetState:
    next_commit_offset: int
    processed_offsets: set[int] = field(default_factory=set)


@dataclass
class OffsetCommitTracker:
    partition_states: dict[TopicPartition, PartitionOffsetState] = field(
        default_factory=dict
    )

    def mark_processed(self, topic: str, partition: int, offset: int) -> None:
        topic_partition = TopicPartition(topic, partition)
        state = self.partition_states.get(topic_partition)

        if state is None:
            self.partition_states[topic_partition] = PartitionOffsetState(
                next_commit_offset=offset,
                processed_offsets={offset},
            )
            return

        state.processed_offsets.add(offset)

    def build_commit_offsets(self) -> dict[TopicPartition, OffsetAndMetadata]:
        commit_offsets: dict[TopicPartition, OffsetAndMetadata] = {}

        for topic_partition, state in self.partition_states.items():
            next_commit_offset = state.next_commit_offset
            while next_commit_offset in state.processed_offsets:
                next_commit_offset += 1

            if next_commit_offset == state.next_commit_offset:
                continue

            commit_offsets[topic_partition] = OffsetAndMetadata(
                offset=next_commit_offset,
                metadata=None,
                leader_epoch=-1,
            )

        return commit_offsets

    def mark_committed(
        self, commit_offsets: dict[TopicPartition, OffsetAndMetadata]
    ) -> None:
        for topic_partition, offset_and_metadata in commit_offsets.items():
            state = self.partition_states[topic_partition]

            for offset in range(
                state.next_commit_offset,
                offset_and_metadata.offset,
            ):
                state.processed_offsets.remove(offset)

            state.next_commit_offset = offset_and_metadata.offset
