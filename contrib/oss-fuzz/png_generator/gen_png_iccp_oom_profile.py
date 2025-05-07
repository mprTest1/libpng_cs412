# gen_png_iccp_oom_profile.py
import zlib
import struct
from png_generator_utils import (
    create_minimal_png_structure,
    create_iccp_chunk,
    write_png
)

def generate_oom_profile_iccp_png(filename="iccp_oom_profile.png"):
    profile_name_str = "LargeProfileOOM"
    compression_method_byte = b"\x00"

    # 创建一个虚拟的 ICC 配置文件头部，其中声明的未压缩大小非常大
    declared_profile_size_uncompressed = 8000000 + 200  # 必须大于 limited_malloc 的阈值

    # 构建一个最小的未压缩 ICC 头部 (132 字节)
    uncompressed_icc_header = struct.pack('>I', declared_profile_size_uncompressed) # Profile 大小
    uncompressed_icc_header += b'OMPF'  # CMM 类型示例
    uncompressed_icc_header += struct.pack('>I', 0x02100000) # 版本 2.1.0
    uncompressed_icc_header += b'mntr'  # Profile 类别 'mntr'
    uncompressed_icc_header += b'RGB '  # 颜色空间 'RGB '
    uncompressed_icc_header += b'XYZ '  # PCS 'XYZ '
    # 用零填充剩余的头部空间，直到132字节
    uncompressed_icc_header += b'\x00' * (132 - len(uncompressed_icc_header))

    # 实际要压缩的数据可以很小，只有头部中声明的大小对OOM测试重要。
    # 但它必须足够有效以通过分配前的初步检查。
    # 在头部之后包含一个最小的标签表结构。
    # 标签数量: 0 (为了此OOM测试的简单性，避免需要标签数据)
    uncompressed_icc_content_for_oom = uncompressed_icc_header + struct.pack('>I', 0) # 头部 + 0 个标签

    compressed_profile_data_for_oom = zlib.compress(uncompressed_icc_content_for_oom)

    iccp_chunk = create_iccp_chunk(profile_name_str, compression_method_byte, compressed_profile_data_for_oom)

    sig, ihdr, idat, iend = create_minimal_png_structure(width=1, height=1, color_type=2, bit_depth=8)

    write_png(filename, [sig, ihdr, iccp_chunk, idat, iend])

if __name__ == "__main__":
    generate_oom_profile_iccp_png()