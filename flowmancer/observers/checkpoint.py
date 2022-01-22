import time, os, pickle
from typing import Dict
from pathlib import Path
from .observer import Observer
from ..typedefs.enums import ExecutionState

class Checkpoint(Observer):
    def __init__(self, **kwargs) -> None:
        self._checkpoint_name = kwargs["checkpoint_name"]
        self._checkpoint_dir = Path(kwargs["checkpoint_dir"])
        self._checkpoint = 0

    def on_restart(self) -> None:
        for name, state in self._load_checkpoint().items():
            if state in (ExecutionState.COMPLETED, ExecutionState.SKIP):
                self.executors.set_state_for_executor(name, state)

    def update(self) -> None:
        if (time.time() - self._checkpoint) >= 10:
            self._checkpoint = time.time()
            self._write_checkpoint()

    def on_success(self) -> None:
        # Checkpoint not needed for successful jobs.
        self._delete_checkpoint()

    def on_failure(self) -> None:
        # One final write to ensure final status is accurately captured.
        self._write_checkpoint()
    
    def _checkpoint_exists(self) -> bool:
        return (self._checkpoint_dir / self._checkpoint_name).exists()

    def _delete_checkpoint(self) -> None:
        if self._checkpoint_exists():
            os.unlink(self._checkpoint_dir / self._checkpoint_name)

    def _write_checkpoint(self) -> None:
        states = {
            ex.name: ex.state
            for ex in self.executors.values()
        }
        checkpoint = { "states": states }
        tmp = self._checkpoint_dir / (self._checkpoint_name+".tmp")
        perm = self._checkpoint_dir / self._checkpoint_name
        pickle.dump(checkpoint, open(tmp, 'wb'))
        if os.path.isfile(perm):
            os.unlink(perm)
        os.rename(tmp, perm)
    
    def _load_checkpoint(self) -> Dict[str, ExecutionState]:
        checkpoint_file = Path(self._checkpoint_dir) / self._checkpoint_name
        if not checkpoint_file.exists():
            return dict()
        checkpoint = pickle.load(open(checkpoint_file, "rb"))
        return checkpoint["states"]