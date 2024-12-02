import numpy as np
from multiprocessing.shared_memory import SharedMemory
from pydantic import Field
from hypha_rpc.sync import connect_to_server, login
from hypha_rpc.utils.schema import schema_function
from typing import Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the SharedImage class
class SharedImage:
    def __init__(self, shm_name: str, shape: tuple, dtype: str):
        self.shm_name = shm_name
        self.shape = shape
        self.dtype = dtype

    @staticmethod
    def from_buffer(buffer: np.ndarray) -> "SharedImage":
        """Create a SharedImage from an existing numpy array buffer."""
        shm = SharedMemory(create=True, size=buffer.nbytes)
        np_array = np.ndarray(buffer.shape, dtype=buffer.dtype, buffer=shm.buf)
        np_array[:] = buffer
        return SharedImage(shm_name=shm.name, shape=buffer.shape, dtype=str(buffer.dtype))

    def to_numpy(self) -> np.ndarray:
        """Restore the numpy array from shared memory."""
        shm = SharedMemory(name=self.shm_name)
        return np.ndarray(self.shape, dtype=self.dtype, buffer=shm.buf)

    def close(self):
        """Close the shared memory."""
        shm = SharedMemory(name=self.shm_name)
        shm.close()

    @staticmethod
    def encode(obj) -> dict:
        """Encode a SharedImage into a transferable format."""
        return {
            "_rtype": "shared-image",
            "shm_name": obj.shm_name,
            "shape": obj.shape,
            "dtype": obj.dtype,
        }

    @staticmethod
    def decode(obj) -> "SharedImage":
        """Decode a transferable format into a SharedImage."""
        assert obj["_rtype"] == "shared-image"
        return SharedImage(
            shm_name=obj["shm_name"],
            shape=tuple(obj["shape"]),
            dtype=obj["dtype"],
        )


# Register the SharedImage codec
def register_shared_image_codec(server):
    """Register the SharedImage codec."""
    server.register_codec({
        "name": "shared-image",
        "type": SharedImage,
        "encoder": SharedImage.encode,
        "decoder": SharedImage.decode,
    })


# Define schema functions for the microscope
@schema_function
def move_stage(
    x: float = Field(..., description="X offset for the microscope stage"),
    y: float = Field(..., description="Y offset for the microscope stage")
) -> str:
    """Move the microscope stage to the specified position."""
    logger.info(f"Moving stage to x={x}, y={y}")
    return f"Stage moved to x={x}, y={y}"


@schema_function
def snap_image(
    exposure: float = Field(..., description="Exposure time in milliseconds"),
    return_shared: bool = Field(True, description="Return SharedImage or numpy array")
) -> Union[SharedImage, np.ndarray]:
    """Snap an image and return either a SharedImage object or numpy array."""
    logger.info(f"Snapping image with exposure={exposure}ms")

    # Simulate image data
    image_data = (np.random.rand(512, 512) * 255).astype(np.uint8)

    if return_shared:
        return SharedImage.from_buffer(image_data)
    else:
        return image_data


# Main function to connect to the Hypha server and register the service
def main():
    server_url = "http://127.0.0.1:9527/"
    token = login({"server_url": server_url})
    server = connect_to_server({"server_url": server_url, "token": token})

    # Register codecs
    register_shared_image_codec(server)

    # Register the microscope service
    svc = server.register_service({
        "name": "Microscope Control",
        "id": "microscope-control",
        "config": {
            "visibility": "public",
            "run_in_executor": True,
        },
        "description": "Control the microscope stage and capture images.",
        "move_stage": move_stage,
        "snap_image": snap_image,
    })

    print(f"Microscope control service registered, available at {server.config.public_base_url}/{server.config.workspace}/services/{svc.id.split('/')[1]}")
    print(f"You can try the server using its HTTP proxy at {server.config.public_base_url}/{server.config.workspace}/services/{svc.id.split('/')[1]}/snap_image?exposure=100&return_shared=true")
    print("Press Ctrl+C to stop the server")
    server.serve()


# Entry point
if __name__ == "__main__":
    main()
