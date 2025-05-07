# png_generator_utils.py
import zlib
import struct

def create_minimal_png_structure(width=1, height=1, color_type=2, bit_depth=8):
    """
    创建 PNG 文件的基本结构组件 (签名, IHDR, IDAT, IEND)。
    color_type:
        0: Grayscale
        2: Truecolor (RGB) <- 适用于带 RGB ICC Profile 的情况
        3: Indexed-color
        4: Grayscale with alpha
        6: Truecolor with alpha
    """
    # PNG Signature
    png_signature = b"\x89PNG\r\n\x1a\n"

    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, bit_depth, color_type, 0, 0, 0)
    ihdr_chunk_body = b'IHDR' + ihdr_data
    ihdr_chunk = struct.pack('>I', len(ihdr_data)) + ihdr_chunk_body + zlib.crc32(ihdr_chunk_body).to_bytes(4, 'big')

    # IDAT (minimal, content depends on IHDR)
    if color_type == 0: # Grayscale, 1 channel
        bytes_per_pixel = (bit_depth + 7) // 8
        scanline_data = b'\x00' * (1 + width * bytes_per_pixel) # Filter byte + pixel data
    elif color_type == 2: # RGB, 3 channels
        bytes_per_pixel = (bit_depth + 7) // 8
        scanline_data = b'\x00' * (1 + width * 3 * bytes_per_pixel)
    elif color_type == 3: # Indexed, 1 channel (requires PLTE chunk, not handled here for simplicity)
        bytes_per_pixel = (bit_depth + 7) // 8
        scanline_data = b'\x00' * (1 + width * bytes_per_pixel) # Placeholder
    elif color_type == 4: # Grayscale + Alpha, 2 channels
        bytes_per_pixel = (bit_depth + 7) // 8
        scanline_data = b'\x00' * (1 + width * 2 * bytes_per_pixel)
    elif color_type == 6: # RGBA, 4 channels
        bytes_per_pixel = (bit_depth + 7) // 8
        scanline_data = b'\x00' * (1 + width * 4 * bytes_per_pixel)
    else:
        scanline_data = b'\x00\x00' # Fallback minimal scanline (filter + 1 byte data)

    idat_compressed_data = zlib.compress(scanline_data)
    idat_chunk_body = b'IDAT' + idat_compressed_data
    idat_chunk = struct.pack('>I', len(idat_compressed_data)) + idat_chunk_body + zlib.crc32(idat_chunk_body).to_bytes(4, 'big')

    # IEND
    iend_chunk_body = b'IEND'
    iend_chunk = struct.pack('>I', 0) + iend_chunk_body + zlib.crc32(iend_chunk_body).to_bytes(4, 'big')

    return png_signature, ihdr_chunk, idat_chunk, iend_chunk

def create_iccp_chunk(profile_name_str, compression_method_byte, compressed_profile_data):
    """创建 iCCP 数据块"""
    profile_name_bytes = profile_name_str.encode('ascii', 'ignore') + b'\x00'
    if len(profile_name_bytes) > 80: # Keyword max 79 chars + null
        profile_name_bytes = profile_name_bytes[:79] + b'\x00'

    iccp_data = profile_name_bytes + compression_method_byte + compressed_profile_data
    chunk_len = len(iccp_data)
    iccp_chunk_body = b'iCCP' + iccp_data
    crc = zlib.crc32(iccp_chunk_body).to_bytes(4, 'big')
    return struct.pack('>I', chunk_len) + iccp_chunk_body + crc

def write_png(filename, components):
    """将 PNG 组件写入文件"""
    with open(filename, "wb") as f:
        for component in components:
            f.write(component)
    print(f"PNG 文件已创建: {filename}")

# --- 修正后的最小化 ICC Profile (用于解析测试) ---
minimal_icc_profile_uncompressed_hex_str = (
    "000000d4"  # Profile Size (224 bytes)
    # 以下是将ASCII转换为HEX的修正：
    "54455354"  # CMM Type 'TEST' (was "TEST") -> 'T'=54, 'E'=45, 'S'=53, 'T'=54
    "02100000"  # Version 2.1.0
    "6d6e7472"  # Profile Class 'mntr' (already hex for 'mntr')
    "52474220"  # Color Space 'RGB ' (already hex for 'RGB ')
    "58595a20"  # PCS 'XYZ ' (already hex for 'XYZ ')
    "000000000000000000000000"  # Date (12 bytes, zeroed)
    "61637370"  # 'acsp' signature (already hex for 'acsp')
    "4150504c"  # Primary Platform 'APPL' (already hex for 'APPL')
    "00000000"  # Profile Flags (zeroed)
    "00000000"  # Device Manufacturer (zeroed)
    "00000000"  # Device Model (zeroed)
    "0000000000000000"  # Device Attributes (8 bytes, zeroed)
    "00000000"  # Rendering Intent (0 - perceptual)
    "f6c601000000d33a" # PCS Illuminant D50 (12 bytes)
    "43524541"  # Profile Creator 'CREA' (already hex for 'CREA')
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000" # 44 bytes reserved (zeroed)
    # Tag Table (starts at offset 132 = 0x84)
    "00000003"  # Tag Count: 3
    # Tag 1: 'desc' (Profile Description)
    "64657363"  # Tag Signature 'desc' (already hex)
    "000000ac"  # Offset to tag data (172)
    "00000010"  # Size of tag data (16 bytes)
    # Tag 2: 'cprt' (Copyright)
    "63707274"  # Tag Signature 'cprt' (already hex)
    "000000bc"  # Offset to tag data (188)
    "00000010"  # Size of tag data (16 bytes)
    # Tag 3: 'wtpt' (White Point XYZType)
    "77747074"  # Tag Signature 'wtpt' (already hex)
    "000000cc"  # Offset to tag data (204)
    "00000014"  # Size of tag data (20 bytes)
    # Tag Data starts at offset 172 (0xAC)
    # 'desc' data: type 'desc' (signature), 4 byte 0, 4 byte string length, string + padding
    # type 'desc' (64657363), reserved (00000000), length of string "Hi\0" is 3 (00000003), string "Hi\0" (486900), padding (00)
    "64657363000000000000000348690000"
    # 'cprt' data: type 'text' (signature), 4 byte 0, string + padding
    # type 'text' (74657874), reserved (00000000), string "Me\0" (4d6500) + 5 padding bytes (0000000000) to make it 8 bytes for string part, total 16 bytes for tag data.
    "74657874000000004d65000000000000"
    # 'wtpt' data: type 'XYZ ' (signature), 4 byte 0, XYZNumber (12b)
    # type 'XYZ ' (58595a20), reserved (00000000), XYZ data (f6c601000000d33a)
    "58595a2000000000f6c601000000d33a"
)

# 从处理过的、纯净的HEX字符串（移除了空格和注释）创建字节
cleaned_hex_str = "".join(minimal_icc_profile_uncompressed_hex_str.replace(" ", "").split())
minimal_icc_profile_bytes = bytes.fromhex(cleaned_hex_str)

# 再次确保声明的大小与实际字节长度匹配
declared_size_in_profile = struct.unpack('>I', minimal_icc_profile_bytes[0:4])[0]
actual_size = len(minimal_icc_profile_bytes)
if declared_size_in_profile != actual_size:
    print(f"警告: 修正后的最小 ICC Profile 的声明大小 {declared_size_in_profile} (0x{declared_size_in_profile:X}) "
          f"与实际大小 {actual_size} (0x{actual_size:X}) 不符。")
    # 如果仍然不符，表示HEX字符串的定义或长度计算存在根本问题。
    # 为了让脚本能运行，这里可以强制更新长度，但这通常意味着profile内容本身与声明不一致。
    # 对于严谨的测试，HEX字符串本身应该是完全正确的。
    # minimal_icc_profile_bytes = struct.pack('>I', actual_size) + minimal_icc_profile_bytes[4:]
    # print(f"警告: 强制将声明大小更新为 {actual_size} (0x{actual_size:X})")