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
#include <assert.h>

#include <vector>

#define PNG_INTERNAL
#include "png.h"

struct PngArrayStream {
  const uint8_t *data;
  size_t size;
  size_t pos;
};

struct PngReader {
  png_structp png_ptr = nullptr;
  png_infop info_ptr = nullptr;
  png_infop end_info = nullptr;
};

void PngArrayStreamCallback(png_structp png_ptr, png_bytep data,
                            png_size_t size) {
  PngArrayStream *stream =
      static_cast<PngArrayStream *>(png_get_io_ptr(png_ptr));
  if (stream->pos + size > stream->size) {
    memset(data, 0, size);
    stream->pos = size;
  } else {
    memcpy(data, &stream->data[stream->pos], size);
    stream->pos += size;
  }
}

static const int kPngHeaderSize = 8;

// Entry point for LibFuzzer.
// Roughly follows the libpng book example:
// http://www.libpng.org/pub/png/book/chapter13.html
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < kPngHeaderSize) {
    return 0;
  }

  std::vector<unsigned char> v(data, data + size);
  if (png_sig_cmp(v.data(), 0, kPngHeaderSize)) {
    // not a PNG.
    return 0;
  }

  PngReader reader;
  reader.png_ptr =
      png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
  assert(reader.png_ptr);
  reader.info_ptr = png_create_info_struct(reader.png_ptr);
  assert(reader.info_ptr);
  reader.end_info = png_create_info_struct(reader.png_ptr);
  assert(reader.end_info);

  // TODO:png_set_error_fn(reader.png_ptr, png_get_error_ptr(reader.png_ptr),
                  //  PngErrorHandler, PngWarningHandler);
  
  PngArrayStream stream{data, size, 0};
  
  png_set_read_fn(reader.png_ptr, &stream, PngArrayStreamCallback);
  
  if (setjmp(png_jmpbuf(reader.png_ptr))) {
    png_destroy_read_struct(&reader.png_ptr, &reader.info_ptr, &reader.end_info);
    return 0;
  }

  // Reading.
  png_read_info(reader.png_ptr, reader.info_ptr);

  // reset error handler to put png_deleter into scope.
  if (setjmp(png_jmpbuf(reader.png_ptr))) {
    png_destroy_read_struct(&reader.png_ptr, &reader.info_ptr, &reader.end_info);
    return 0;
  }

  png_uint_32 width, height;
  int bit_depth, color_type, interlace_type, compression_type;
  int filter_type;

  if (!png_get_IHDR(reader.png_ptr, reader.info_ptr, &width,
                    &height, &bit_depth, &color_type, &interlace_type,
                    &compression_type, &filter_type)) {
    png_destroy_read_struct(&reader.png_ptr, &reader.info_ptr, &reader.end_info);
    return 0;
  }

  const size_t kMaxImageSize = 1 << 20;
  const size_t kMaxHeight = 1 << 10;
  if ((uint64_t)width * height > kMaxImageSize) return 0;
  if (height > kMaxHeight) return 0;

  if (setjmp(png_jmpbuf(reader.png_ptr)) == 0) {
    png_set_read_fn(reader.png_ptr, &stream, PngArrayStreamCallback);

    int transforms_value = size >= 24 ? (*(int*)&data[size-16]) : ~0;
    png_read_png(reader.png_ptr, reader.info_ptr, transforms_value, nullptr);
  }
  png_destroy_read_struct(&reader.png_ptr, &reader.info_ptr, &reader.end_info);

#ifdef PNG_SIMPLIFIED_READ_SUPPORTED
  // Simplified READ API
  png_image image;
  memset(&image, 0, (sizeof image));
  image.version = PNG_IMAGE_VERSION;

  if (!png_image_begin_read_from_memory(&image, data, size)) {
    return 0;
  }

  image.format = PNG_FORMAT_RGBA;
  std::vector<png_byte> buffer(PNG_IMAGE_SIZE(image));
  png_image_finish_read(&image, NULL, buffer.data(), 0, NULL);
#endif

  return 0;
}
