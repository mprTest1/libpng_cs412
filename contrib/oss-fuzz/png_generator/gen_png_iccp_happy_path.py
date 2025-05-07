# gen_png_iccp_happy_path.py
import zlib
from png_generator_utils import (
    create_minimal_png_structure,
    create_iccp_chunk,
    write_png,
    minimal_icc_profile_bytes
)

def generate_happy_path_png(filename="iccp_happy_path.png"):
    profile_name = "TestProfileValid"
    compression_method = b"\x00"  # zlib/deflate

    # 使用已定义的 minimal_icc_profile_bytes
    compressed_profile = zlib.compress(minimal_icc_profile_bytes)

    iccp_chunk = create_iccp_chunk(profile_name, compression_method, compressed_profile)

    # 创建一个 RGB 图像，因为 ICC Profile 通常用于颜色管理
    sig, ihdr, idat, iend = create_minimal_png_structure(width=1, height=1, color_type=2, bit_depth=8)

    write_png(filename, [sig, ihdr, iccp_chunk, idat, iend])

if __name__ == "__main__":
    generate_happy_path_png()