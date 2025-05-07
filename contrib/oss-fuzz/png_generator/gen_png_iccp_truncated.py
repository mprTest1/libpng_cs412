# gen_png_iccp_truncated.py
import zlib
from png_generator_utils import (
    create_minimal_png_structure,
    create_iccp_chunk,
    write_png,
    minimal_icc_profile_bytes
)

def generate_truncated_iccp_png(filename="iccp_truncated.png"):
    profile_name = "TruncatedProfile"
    compression_method = b"\x00"

    compressed_profile_full = zlib.compress(minimal_icc_profile_bytes)
    # 截断压缩数据
    if len(compressed_profile_full) > 20:
        truncated_compressed_profile = compressed_profile_full[:-20] # 删除最后20字节
    elif len(compressed_profile_full) > 1:
        truncated_compressed_profile = compressed_profile_full[:len(compressed_profile_full)//2] # 或取一半
    else:
        truncated_compressed_profile = b'' # 如果太短则为空

    iccp_chunk = create_iccp_chunk(profile_name, compression_method, truncated_compressed_profile)

    sig, ihdr, idat, iend = create_minimal_png_structure(width=1, height=1, color_type=2, bit_depth=8)

    write_png(filename, [sig, ihdr, iccp_chunk, idat, iend])

if __name__ == "__main__":
    generate_truncated_iccp_png()