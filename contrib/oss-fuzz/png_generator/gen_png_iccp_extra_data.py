# gen_png_iccp_extra_data.py
import zlib
from png_generator_utils import (
    create_minimal_png_structure,
    create_iccp_chunk,
    write_png,
    minimal_icc_profile_bytes
)

def generate_extra_data_iccp_png(filename="iccp_extra_data.png"):
    profile_name = "ExtraDataProfile"
    compression_method = b"\x00"

    uncompressed_data_with_extra = minimal_icc_profile_bytes + (b"GARBAGE_DATA_AFTER_PROFILE_ENDS_HERE" * 3)

    compressed_profile_with_extra = zlib.compress(uncompressed_data_with_extra)

    iccp_chunk = create_iccp_chunk(profile_name, compression_method, compressed_profile_with_extra)

    sig, ihdr, idat, iend = create_minimal_png_structure(width=1, height=1, color_type=2, bit_depth=8)

    write_png(filename, [sig, ihdr, iccp_chunk, idat, iend])

if __name__ == "__main__":
    generate_extra_data_iccp_png()