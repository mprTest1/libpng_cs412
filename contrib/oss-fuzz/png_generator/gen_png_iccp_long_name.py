# gen_png_iccp_long_name.py
import zlib
from png_generator_utils import (
    create_minimal_png_structure,
    create_iccp_chunk,
    write_png,
    minimal_icc_profile_bytes
)

def generate_long_name_iccp_png(filename="iccp_long_name.png"):
    # iCCP 关键字（配置文件名称）最大长度为 79 个字符 + 空终止符
    profile_name = "A" * 79
    compression_method = b"\x00"

    # 为此测试使用一个标准的、小的压缩配置文件
    compressed_profile = zlib.compress(minimal_icc_profile_bytes)

    iccp_chunk = create_iccp_chunk(profile_name, compression_method, compressed_profile)

    sig, ihdr, idat, iend = create_minimal_png_structure(width=1, height=1, color_type=2, bit_depth=8)

    write_png(filename, [sig, ihdr, iccp_chunk, idat, iend])

if __name__ == "__main__":
    print("注意: 此 PNG 旨在尝试使用最大长度的 iCCP 配置文件名称。")
    print("对于标准的 limited_malloc 设置，它不太可能为名称本身触发内存不足。")
    generate_long_name_iccp_png()