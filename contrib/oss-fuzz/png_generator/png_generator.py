import zlib
import struct

# 示例：为“配置文件缓冲区内存不足”制作输入
profile_name = b"LargeProfile\x00"  # 配置文件名称
compression_method = b"\x00"  # 压缩方法

# 虚拟 ICC 头部 (132 字节)
# 前 4 字节: profile_size (设置得非常大)
# (PNG 整数使用大端字节序，但 ICC 配置文件长度通常也是大端)
declared_profile_size = 8000000 + 100 # 使其超过 limited_malloc 的阈值
uncompressed_icc_header = struct.pack('>I', declared_profile_size) # 配置文件长度
uncompressed_icc_header += b'mHLS' # CMM 类型示例
uncompressed_icc_header += struct.pack('>I', 0x02100000) # 版本 2.1.0
uncompressed_icc_header += b'mntr' # 配置文件类别: 显示设备
uncompressed_icc_header += b'RGB ' # 颜色空间
uncompressed_icc_header += b'XYZ ' # PCS
uncompressed_icc_header += b'\x00' * (132 - len(uncompressed_icc_header)) # 填充到 132 字节

# 头部之后用于 zlib 压缩的最小实际数据
uncompressed_icc_data = uncompressed_icc_header + b"minimal_data_after_header"

compressed_profile_data = zlib.compress(uncompressed_icc_data)

iccp_chunk_data = profile_name + compression_method + compressed_profile_data
iccp_chunk_len = len(iccp_chunk_data)

# --- PNG 文件结构 ---
png_signature = b"\x89PNG\r\n\x1a\n"

# IHDR (最小: 1x1 像素, 8位深度, RGB)
ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0) # 宽度, 高度, 位深度, 颜色类型, 压缩, 滤波, 交错
ihdr_chunk = struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + zlib.crc32(b'IHDR' + ihdr_data).to_bytes(4, 'big')

# iCCP 数据块
# 对于使用 CRC_QUIET_USE 的模糊测试，实际的 CRC 值可能不那么重要
# 但为了完整性:
iccp_crc = zlib.crc32(b'iCCP' + iccp_chunk_data).to_bytes(4, 'big')
iccp_chunk = struct.pack('>I', iccp_chunk_len) + b'iCCP' + iccp_chunk_data + iccp_crc

# IDAT (最小: 一个压缩像素，实际内容取决于滤波器类型和 IHDR)
# 对于 1x1 RGB8 图像，行为 [滤波器字节, R, G, B]。最简单的滤波器 0: [0,0,0,0]
# 对于模糊测试，一个最小有效的 IDAT 就足够了。
# 此示例使用一个预先准备好的用于 1x1 透明像素的最小 IDAT。
idat_data = zlib.decompress(bytes.fromhex('789c6300010000050001')) # 用于单个像素的最小 zlib 流
idat_chunk = struct.pack('>I', len(idat_data)) + b'IDAT' + idat_data + zlib.crc32(b'IDAT' + idat_data).to_bytes(4, 'big')

# IEND
iend_chunk = struct.pack('>I', 0) + b'IEND' + zlib.crc32(b'IEND').to_bytes(4, 'big')

# 组装 PNG
crafted_png = png_signature + ihdr_chunk + iccp_chunk + idat_chunk + iend_chunk

with open("crafted_oom_iccp.png", "wb") as f:
    f.write(crafted_png)
print("crafted_oom_iccp.png 已创建。")

# 类似地，对于“正常路径”的 iCCP - 您需要加载一个真实的小 ICC 文件，然后用 zlib.compress 压缩它。
# 对于截断的 zlib，对 compressed_profile_data 进行切片。
# 对于额外数据，在压缩前将其附加到 uncompressed_icc_data。