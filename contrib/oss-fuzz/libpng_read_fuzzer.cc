// libpng_read_fuzzer.cc
// Copyright 2017-2018 Glenn Randers-Pehrson
// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that may
// be found in the LICENSE file https://cs.chromium.org/chromium/src/LICENSE

// The modifications in 2017 by Glenn Randers-Pehrson include
// 1. addition of a PNG_CLEANUP macro,
// 2. setting the option to ignore ADLER32 checksums,
// 3. adding "#include <string.h>" which is needed on some platforms
//    to provide memcpy().
// 4. adding read_end_info() and creating an end_info structure.
// 5. adding calls to png_set_*() transforms commonly used by browsers.

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <random>
#include <iostream>

#include <vector>

#define PNG_INTERNAL
#include "png.h"

#define PNG_CLEANUP \
  if(png_handler.png_ptr) \
  { \
    if (png_handler.row_ptr) \
      png_free(png_handler.png_ptr, png_handler.row_ptr); \
    if (png_handler.end_info_ptr) \
      png_destroy_read_struct(&png_handler.png_ptr, &png_handler.info_ptr,\
        &png_handler.end_info_ptr); \
    else if (png_handler.info_ptr) \
      png_destroy_read_struct(&png_handler.png_ptr, &png_handler.info_ptr,\
        nullptr); \
    else \
      png_destroy_read_struct(&png_handler.png_ptr, nullptr, nullptr); \
    png_handler.png_ptr = nullptr; \
    png_handler.row_ptr = nullptr; \
    png_handler.info_ptr = nullptr; \
    png_handler.end_info_ptr = nullptr; \
  }

struct BufState {
  const uint8_t* data;
  size_t bytes_left;
};

struct PngObjectHandler {
  png_infop info_ptr = nullptr;
  png_structp png_ptr = nullptr;
  png_infop end_info_ptr = nullptr;
  png_voidp row_ptr = nullptr;
  BufState* buf_state = nullptr;

  ~PngObjectHandler() {
    if (row_ptr)
      png_free(png_ptr, row_ptr);
    if (end_info_ptr)
      png_destroy_read_struct(&png_ptr, &info_ptr, &end_info_ptr);
    else if (info_ptr)
      png_destroy_read_struct(&png_ptr, &info_ptr, nullptr);
    else
      png_destroy_read_struct(&png_ptr, nullptr, nullptr);
    delete buf_state;
  }
};

void user_read_data(png_structp png_ptr, png_bytep data, size_t length) {
  BufState* buf_state = static_cast<BufState*>(png_get_io_ptr(png_ptr));
  if (length > buf_state->bytes_left) {
    png_error(png_ptr, "read error");
  }
  memcpy(data, buf_state->data, length);
  buf_state->bytes_left -= length;
  buf_state->data += length;
}

void* limited_malloc(png_structp, png_alloc_size_t size) {
  // libpng may allocate large amounts of memory that the fuzzer reports as
  // an error. In order to silence these errors, make libpng fail when trying
  // to allocate a large amount. This allocator used to be in the Chromium
  // version of this fuzzer.
  // This number is chosen to match the default png_user_chunk_malloc_max.
  if (size > 8000000)
    return nullptr;

  return malloc(size);
}

void default_free(png_structp, png_voidp ptr) {
  return free(ptr);
}

static const int kPngHeaderSize = 8;
//static const int kTransformBytes = 4; //测png_read_png用
static const int kMinSizeForReadPngTest = kPngHeaderSize /*+ kTransformBytes*/;

// Entry point for LibFuzzer.
// Roughly follows the libpng book example:
// http://www.libpng.org/pub/png/book/chapter13.html
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < kMinSizeForReadPngTest) {
    return 0;
  }

  std::vector<unsigned char> v(data, data + size);
  if (png_sig_cmp(v.data(), 0, kMinSizeForReadPngTest)) {
    // not a PNG.
    return 0;
  }

  PngObjectHandler png_handler;
  png_handler.png_ptr = nullptr;
  png_handler.row_ptr = nullptr;
  png_handler.info_ptr = nullptr;
  png_handler.end_info_ptr = nullptr;

  png_handler.png_ptr = png_create_read_struct
    (PNG_LIBPNG_VER_STRING, nullptr, nullptr, nullptr);
  if (!png_handler.png_ptr) {
    return 0;
  }

  png_handler.info_ptr = png_create_info_struct(png_handler.png_ptr);
  if (!png_handler.info_ptr) {
    PNG_CLEANUP
    return 0;
  }

  png_handler.end_info_ptr = png_create_info_struct(png_handler.png_ptr);
  if (!png_handler.end_info_ptr) {
    PNG_CLEANUP
    return 0;
  }

  // Use a custom allocator that fails for large allocations to avoid OOM.
  png_set_mem_fn(png_handler.png_ptr, nullptr, limited_malloc, default_free);

  png_set_crc_action(png_handler.png_ptr, PNG_CRC_QUIET_USE, PNG_CRC_QUIET_USE);
#ifdef PNG_IGNORE_ADLER32
  png_set_option(png_handler.png_ptr, PNG_IGNORE_ADLER32, PNG_OPTION_ON);
#endif

  // Setting up reading from buffer.
  png_handler.buf_state = new BufState();
  png_handler.buf_state->data = data + kPngHeaderSize;
  png_handler.buf_state->bytes_left = size - kPngHeaderSize;
  png_set_read_fn(png_handler.png_ptr, png_handler.buf_state, user_read_data);
  png_set_sig_bytes(png_handler.png_ptr, kPngHeaderSize);

  if (setjmp(png_jmpbuf(png_handler.png_ptr))) {
    PNG_CLEANUP
    return 0;
  }

  // Reading.
  png_read_info(png_handler.png_ptr, png_handler.info_ptr);
  // read png 恩！情！
  srand(time(NULL));

  int transforms_value = rand();

// 获取行字节数和行指针数组
size_t rowbytes = png_get_rowbytes(png_handler.png_ptr, png_handler.info_ptr);
png_bytepp rows = png_get_rows(png_handler.png_ptr, png_handler.info_ptr);

// 获取基础图像信息
png_uint_32 width = png_get_image_width(png_handler.png_ptr, png_handler.info_ptr);
png_uint_32 height = png_get_image_height(png_handler.png_ptr, png_handler.info_ptr);
png_byte bit_depth = png_get_bit_depth(png_handler.png_ptr, png_handler.info_ptr);
png_byte color_type = png_get_color_type(png_handler.png_ptr, png_handler.info_ptr);
png_byte channels = png_get_channels(png_handler.png_ptr, png_handler.info_ptr);
png_byte interlace_type = png_get_interlace_type(png_handler.png_ptr, png_handler.info_ptr);
png_byte compression_type = png_get_compression_type(png_handler.png_ptr, png_handler.info_ptr);
png_byte filter_type = png_get_filter_type(png_handler.png_ptr, png_handler.info_ptr);

// 获取物理像素密度
png_uint_32 x_pixels = png_get_x_pixels_per_meter(png_handler.png_ptr, png_handler.info_ptr);
png_uint_32 y_pixels = png_get_y_pixels_per_meter(png_handler.png_ptr, png_handler.info_ptr);
png_uint_32 pixels_per_meter = png_get_pixels_per_meter(png_handler.png_ptr, png_handler.info_ptr);

// 获取cHRM（色度坐标）
double white_x, white_y, red_x, red_y, green_x, green_y, blue_x, blue_y;
if (png_get_cHRM(png_handler.png_ptr, png_handler.info_ptr, &white_x, &white_y,
                 &red_x, &red_y, &green_x, &green_y, &blue_x, &blue_y)) {
  // 触发cHRM处理
}

// 获取sBIT（有效位数）
png_color_8p sig_bit;
if (png_get_sBIT(png_handler.png_ptr, png_handler.info_ptr, &sig_bit)) {
  // 触发sBIT处理
}

// 获取hIST（调色板直方图）
png_uint_16p hist;
if (png_get_hIST(png_handler.png_ptr, png_handler.info_ptr, &hist)) {
  // 触发hIST处理
}

// 获取pHYs（物理像素尺寸）
png_uint_32 res_x, res_y;
int unit_type;
if (png_get_pHYs(png_handler.png_ptr, png_handler.info_ptr, &res_x, &res_y, &unit_type)) {
  // 触发pHYs处理
}

// 获取sCAL（物理比例）
int unit;
double scal_width ;
double scal_height ;
if (png_get_sCAL(png_handler.png_ptr, png_handler.info_ptr, &unit, &scal_width, &scal_height)) {
}

// 获取oFFs（图像偏移）
png_int_32 offset_x, offset_y;
int offset_unit;
if (png_get_oFFs(png_handler.png_ptr, png_handler.info_ptr, &offset_x, &offset_y, &offset_unit)) {
  // 触发oFFs处理
}

// 获取pCAL（像素校准）
png_charp purpose, units;
png_int_32 X0, X1;
int param_type;
int nparams;
png_charpp params;
if (png_get_pCAL(png_handler.png_ptr, png_handler.info_ptr, &purpose, &X0, &X1, &param_type, &nparams,
                 &units, &params)) {
}

// 获取sPLT（建议调色板）
png_sPLT_tp splt_ptr;
int splt_count;
if (png_get_sPLT(png_handler.png_ptr, png_handler.info_ptr, &splt_ptr)) {
  // 触发sPLT处理
}

// 获取时间和修改时间
png_timep mod_time;
if (png_get_tIME(png_handler.png_ptr, png_handler.info_ptr, &mod_time)) {
  // 触发tIME处理
}

// 获取ICC配置文件
png_charp name;
png_bytep profile;
png_uint_32 proflen;
int compression_type1;
if (png_get_iCCP(png_handler.png_ptr, png_handler.info_ptr, &name, &compression_type1, &profile, &proflen)) {
}

// 获取颜色空间信息


  double gamma;
  if (png_get_gAMA(png_handler.png_ptr, png_handler.info_ptr, &gamma)) {
    // 可记录Gamma值，此处仅用于触发覆盖率
  }

  // 获取调色板信息（触发png_get_PLTE）
  png_colorp palette;
  int num_palette;
  if (png_get_PLTE(png_handler.png_ptr, png_handler.info_ptr, &palette, &num_palette)) {
    // 可处理调色板，此处仅用于触发覆盖率
  }

  // 获取透明色信息（触发png_get_tRNS）
  png_bytep trans_alpha;
  int num_trans;
  png_color_16p trans_color;
  if (png_get_tRNS(png_handler.png_ptr, png_handler.info_ptr, &trans_alpha, &num_trans, &trans_color)) {
    // 可处理透明通道，此处仅用于触发覆盖率
  }

  // 获取文本信息（触发png_get_text）
  png_textp text_ptr;
  int num_text;
  if (png_get_text(png_handler.png_ptr, png_handler.info_ptr, &text_ptr, &num_text)) {
    // 可处理文本块，此处仅用于触发覆盖率
  }

  // 获取背景色（触发png_get_bKGD）
  png_color_16p background;
  if (png_get_bKGD(png_handler.png_ptr, png_handler.info_ptr, &background)) {
    // 可记录背景色，此处仅用于触发覆盖率
  }

  #ifdef PNG_sRGB_SUPPORTED
  int intent;
  png_get_sRGB(png_handler.png_ptr, png_handler.info_ptr, &intent);
#endif

#ifdef PNG_iCCP_SUPPORTED
  // Note: png_get_iCCP is already called, ensure inputs trigger it.
  // You might need to free the returned pointers if they are allocated.
  png_charp iccp_name;
  png_bytep iccp_profile;
  png_uint_32 iccp_proflen;
  int iccp_compression;
  if (png_get_iCCP(png_handler.png_ptr, png_handler.info_ptr, &iccp_name, &iccp_compression, &iccp_profile, &iccp_proflen)) {
     // png_free(...) might be needed here depending on how libpng handles memory for iCCP in fuzzing context.
     // Check libpng documentation/code for memory management of returned profile.
     // The existing code already frees name and profile, which is good.
  }
#endif


#ifdef PNG_sPLT_SUPPORTED
  // Note: png_get_sPLT is already called. Ensure inputs trigger it.
  png_sPLT_tp splt_entry;
  int num_splt;
  num_splt = png_get_sPLT(png_handler.png_ptr, png_handler.info_ptr, &splt_entry);
  // No need to free splt_entry here, it points into info_ptr.
#endif

#ifdef PNG_cICP_SUPPORTED
  png_byte cp, tf, mc, vf;
  png_get_cICP(png_handler.png_ptr, png_handler.info_ptr, &cp, &tf, &mc, &vf);
#endif

#ifdef PNG_cLLI_SUPPORTED
#ifdef PNG_FLOATING_POINT_SUPPORTED
  double clli_max_cll, clli_max_fall;
  png_get_cLLI(png_handler.png_ptr, png_handler.info_ptr, &clli_max_cll, &clli_max_fall);
#endif
#ifdef PNG_FIXED_POINT_SUPPORTED
  png_uint_32 clli_max_cll_fixed, clli_max_fall_fixed;
  png_get_cLLI_fixed(png_handler.png_ptr, png_handler.info_ptr, &clli_max_cll_fixed, &clli_max_fall_fixed);
#endif
#endif // PNG_cLLI_SUPPORTED


#ifdef PNG_mDCV_SUPPORTED
  // Add calls for png_get_mDCV and png_get_mDCV_fixed similarly
#endif

#ifdef PNG_eXIf_SUPPORTED
  png_bytep exif_data;
  png_uint_32 num_exif;
  png_get_eXIf_1(png_handler.png_ptr, png_handler.info_ptr, &num_exif, &exif_data);
  // Note: exif_data points into info_ptr, no free needed here.
#endif

#ifdef PNG_hIST_SUPPORTED
  // Note: png_get_hIST is already called. Ensure inputs trigger it.
  png_uint_16p hist_data;
  png_get_hIST(png_handler.png_ptr, png_handler.info_ptr, &hist_data);
#endif

#ifdef PNG_sBIT_SUPPORTED
  // Note: png_get_sBIT is already called. Ensure inputs trigger it.
  png_color_8p sbit_data;
  png_get_sBIT(png_handler.png_ptr, png_handler.info_ptr, &sbit_data);
#endif


#ifdef PNG_tIME_SUPPORTED
  // Note: png_get_tIME is already called. Ensure inputs trigger it.
  png_timep time_data;
  png_get_tIME(png_handler.png_ptr, png_handler.info_ptr, &time_data);
#endif


// --- Calls for status/limit functions ---
#ifdef PNG_READ_RGB_TO_GRAY_SUPPORTED
  png_byte rgb_to_gray_status = png_get_rgb_to_gray_status(png_handler.png_ptr);
#endif

#ifdef PNG_USER_CHUNKS_SUPPORTED
  png_voidp user_chunk_ptr = png_get_user_chunk_ptr(png_handler.png_ptr);
#endif

  size_t compression_buffer_size = png_get_compression_buffer_size(png_handler.png_ptr);

#ifdef PNG_SET_USER_LIMITS_SUPPORTED
  png_uint_32 user_width_max = png_get_user_width_max(png_handler.png_ptr);
  png_uint_32 user_height_max = png_get_user_height_max(png_handler.png_ptr);
  png_uint_32 chunk_cache_max = png_get_chunk_cache_max(png_handler.png_ptr);
  png_alloc_size_t chunk_malloc_max = png_get_chunk_malloc_max(png_handler.png_ptr);
#endif

#ifdef PNG_IO_STATE_SUPPORTED
  png_uint_32 io_state = png_get_io_state(png_handler.png_ptr);
  png_uint_32 io_chunk_type = png_get_io_chunk_type(png_handler.png_ptr);
#endif

#ifdef PNG_CHECK_FOR_INVALID_INDEX_SUPPORTED
#ifdef PNG_GET_PALETTE_MAX_SUPPORTED
  int palette_max = png_get_palette_max(png_handler.png_ptr, png_handler.info_ptr);
#endif
#endif


// ... rest of the fuzzer, including png_read_update_info, reading rows, etc. ...

// --- Call png_get_unknown_chunks after reading is finished ---
#ifdef PNG_STORE_UNKNOWN_CHUNKS_SUPPORTED
  // Make sure png_set_keep_unknown_chunks was called earlier
  png_unknown_chunkp unknowns;
  int num_unknowns = png_get_unknown_chunks(png_handler.png_ptr, png_handler.info_ptr, &unknowns);
#endif

  // --------------------- 新增：设置更多转换选项触发pngtrans.c逻辑 ---------------------
  // 设置背景色混合（触发pngtrans.c中的背景处理逻辑）
  png_color_16 bg_color = {0, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF};
  png_set_background(png_handler.png_ptr, &bg_color, PNG_BACKGROUND_GAMMA_SCREEN, 0, 1.0);

  // 启用BGR像素格式（触发颜色空间转换）
  png_set_bgr(png_handler.png_ptr);

  // 设置Alpha预乘模式（触发Alpha处理逻辑）
  png_set_alpha_mode(png_handler.png_ptr, PNG_ALPHA_PREMULTIPLIED, PNG_DEFAULT_sRGB);

  // 启用像素打包（针对低比特深度图像）
  png_set_packing(png_handler.png_ptr);

  // 其他可能影响pngtrans.c的选项
  png_set_invert_alpha(png_handler.png_ptr);  // 反转Alpha通道
  png_set_gray_to_rgb(png_handler.png_ptr);   // 强制灰度转RGB（覆盖更多转换分支）

  // reset error handler to put png_deleter into scope.
  if (setjmp(png_jmpbuf(png_handler.png_ptr))) {
    PNG_CLEANUP
    return 0;
  }

  
  int bit_depth1, color_type1, interlace_type1;
  int filter_type1;

  if (!png_get_IHDR(png_handler.png_ptr, png_handler.info_ptr, &width,
                    &height, &bit_depth1, &color_type1, &interlace_type1,
                    &compression_type1, &filter_type1)) {
    PNG_CLEANUP
    return 0;
  }

  // This is going to be too slow.
  if (width && height > 100000000 / width) {
    PNG_CLEANUP
    return 0;
  }

  // Set several transforms that browsers typically use:
  png_set_gray_to_rgb(png_handler.png_ptr);
  png_set_expand(png_handler.png_ptr);
  png_set_packing(png_handler.png_ptr);
  png_set_scale_16(png_handler.png_ptr);
  png_set_tRNS_to_alpha(png_handler.png_ptr);

  int passes = png_set_interlace_handling(png_handler.png_ptr);

  png_read_update_info(png_handler.png_ptr, png_handler.info_ptr);

  int channels1 = png_get_channels(png_handler.png_ptr, png_handler.info_ptr);
  // 获取颜色类型（再次触发png_get_IHDR）
  png_get_IHDR(png_handler.png_ptr, png_handler.info_ptr, &width, &height,
               &bit_depth1, &color_type1, &interlace_type1, &compression_type1, &filter_type1);

  png_handler.row_ptr = png_malloc(
      png_handler.png_ptr, png_get_rowbytes(png_handler.png_ptr,
                                            png_handler.info_ptr));

  for (int pass = 0; pass < passes; ++pass) {
    for (png_uint_32 y = 0; y < height; ++y) {
      png_read_row(png_handler.png_ptr,
                   static_cast<png_bytep>(png_handler.row_ptr), nullptr);
    }
  }

  png_read_end(png_handler.png_ptr, png_handler.end_info_ptr);

  png_read_png(png_handler.png_ptr, png_handler.info_ptr, transforms_value, NULL); //将军的恩情还不完

  PNG_CLEANUP

  
  return 0;
}
