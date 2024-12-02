import numpy as np
from multiprocessing.shared_memory import SharedMemory
from scipy.signal import convolve2d
from hypha_rpc.sync import connect_to_server, login
from hypha_rpc.utils.schema import schema_function
from pydantic import Field
import logging
from microscope import SharedImage, register_shared_image_codec

# Set up logging
# print to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the convolution function
@schema_function
def convolve_image(
    image: SharedImage = Field(..., description="Input image as a SharedImage"),
    kernel_size: int = Field(3, description="Kernel size for the convolution filter"),
) -> SharedImage:
    """Apply a convolution filter with the specified kernel size."""
    logger.info(f"Convolving image with kernel size={kernel_size}")

    # Restore the image from shared memory
    image_data = image.to_numpy()

    # Generate a kernel (e.g., a simple averaging filter)
    kernel = np.ones((kernel_size, kernel_size), dtype=np.float32) / (kernel_size ** 2)

    # Perform convolution
    convolved_image = convolve2d(image_data, kernel, mode='same', boundary='wrap').astype(np.uint8)

    # Return the convolved image as SharedImage
    return SharedImage.from_buffer(convolved_image)


# Main function to connect to the Hypha server and register the service
def main():
    server_url = "http://127.0.0.1:9527/"
    token = login({"server_url": server_url})
    server = connect_to_server({"server_url": server_url, "token": token, "sync_max_workers": 10})

    # Register codecs
    register_shared_image_codec(server)

    # Register the image analysis service
    svc = server.register_service({
        "name": "Image Analysis",
        "id": "image-analysis",
        "config": {
            "visibility": "public",
            "run_in_executor": True,
        },
        "description": "Apply image analysis functions like convolution.",
        "convolve_image": convolve_image,
    })

    print(f"Image analysis service registered, available at {server.config.public_base_url}/{server.config.workspace}/services/{svc.id.split('/')[1]}")
    print("Press Ctrl+C to stop the server")
    server.serve()


# Entry point
if __name__ == "__main__":
    main()
