import zlib
import struct
import random 
import datetime # Added for tIME chunk
import os
import glob
import sys

randPNG_save_path = 'randPNG_seeds'

class PNG:
    def __init__(self, critical_chunk_config=None, ancillary_chunk_config=None):
        """
        初始化PNG对象。
        critical_chunk_config: 0 (Legal) 1 (Illegal)
        ancillary_chunk_config: 0 (Legal) 1 (Illegal) 2 (Not Used)
        """
        self.data = b'\x89PNG\r\n\x1a\n'

        self.color_type = random.choice([0, 2, 3, 4, 6]) 
        if self.color_type == 0: 
            self.bit_depth = random.choice([1, 2, 4, 8, 16])
        elif self.color_type == 2: 
            self.bit_depth = random.choice([8, 16])
        elif self.color_type == 3: 
            self.bit_depth = random.choice([1, 2, 4, 8])
        elif self.color_type == 4: 
            self.bit_depth = random.choice([8, 16])
        elif self.color_type == 6: 
            self.bit_depth = random.choice([8, 16])
        else: 
            self.bit_depth = 8 

        if self.color_type == 3:
            self.plte_chunk_present = True
            max_entries_for_bd = 1 << self.bit_depth
            self.num_plte_entries = random.randint(1, min(256, max_entries_for_bd))
        else:
            self.plte_chunk_present = random.choice([True, False])
            self.num_plte_entries = 0 
        
        self.width = 1
        self.height = 1

        crit_config = critical_chunk_config if critical_chunk_config is not None else {}
        anc_config = ancillary_chunk_config if ancillary_chunk_config is not None else {}

        self._add_chunk_by_name('IHDR', crit_config.get('IHDR', 0))
        
        self.known_ancillary_chunks_before_plte = ['sBIT', 'gAMA', 'cHRM', 'sRGB', 'cICP', 'eXIf', 'iCCP', 'sPLT'] 
        for chunk_name_str in self.known_ancillary_chunks_before_plte:
            validity_code = anc_config.get(chunk_name_str, 2)
            if validity_code != 2:
                self._add_chunk_by_name(chunk_name_str, validity_code)

        plte_validity_default = 0 if self.color_type == 3 or self.plte_chunk_present else 2
        self._add_chunk_by_name('PLTE', crit_config.get('PLTE', plte_validity_default) )


        self.known_ancillary_chunks_after_plte = [
             'hIST', 'tRNS', 'bKGD', 'pHYs', 'sTER', 
             'tEXt', 'zTXt', 'iTXt', 'tIME', 'dSIG' 
        ] 

        for chunk_name_str in self.known_ancillary_chunks_after_plte:
            validity_code = anc_config.get(chunk_name_str, 2)
            if validity_code != 2:
                self._add_chunk_by_name(chunk_name_str, validity_code)

        self._add_chunk_by_name('IDAT', crit_config.get('IDAT', 0))
        self._add_chunk_by_name('IEND', crit_config.get('IEND', 0))

    def _add_chunk_by_name(self, chunk_name_str, validity_code):
        if validity_code == 2 and chunk_name_str not in ['IHDR', 'PLTE', 'IDAT', 'IEND']: 
            return

        if chunk_name_str == 'IHDR':
            self.add_ihdr_chunk(validity_code)
        elif chunk_name_str == 'PLTE':
            if self.color_type == 3 or self.plte_chunk_present: 
                 if validity_code !=2: 
                    self.add_plte_chunk(validity_code)
            elif validity_code == 0 or validity_code == 1: 
                if validity_code !=2: self.add_plte_chunk(validity_code)
        elif chunk_name_str == 'IDAT':
            self.add_idat_chunk(validity_code)
        elif chunk_name_str == 'IEND':
            self.add_iend_chunk(validity_code)
        elif chunk_name_str == 'bKGD':
            self.add_bkgd_chunk(validity_code)
        elif chunk_name_str == 'cHRM':
            self.add_chrm_chunk(validity_code)
        elif chunk_name_str == 'cICP':
            self.add_cicp_chunk(validity_code)
        elif chunk_name_str == 'gAMA':
            self.add_gama_chunk(validity_code)
        elif chunk_name_str == 'eXIf':
            self.add_exif_chunk(validity_code)
        elif chunk_name_str == 'dSIG':
            self.add_dsig_chunk(validity_code)
        elif chunk_name_str == 'hIST':
            self.add_hist_chunk(validity_code)
        elif chunk_name_str == 'iCCP':
            self.add_iccp_chunk(validity_code)
        elif chunk_name_str == 'iTXt':
            self.add_itxt_chunk(validity_code)
        elif chunk_name_str == 'pHYs':
            self.add_phys_chunk(validity_code)
        elif chunk_name_str == 'sBIT':
            self.add_sbit_chunk(validity_code)
        elif chunk_name_str == 'sPLT':
            self.add_splt_chunk(validity_code)
        elif chunk_name_str == 'sRGB':
            self.add_srgb_chunk(validity_code)
        elif chunk_name_str == 'sTER':
            self.add_ster_chunk(validity_code)
        elif chunk_name_str == 'tEXt':
            self.add_text_chunk(validity_code)
        elif chunk_name_str == 'tIME':
            self.add_time_chunk(validity_code)
        elif chunk_name_str == 'tRNS':
            self.add_trns_chunk(validity_code)
        elif chunk_name_str == 'zTXt':
            self.add_ztxt_chunk(validity_code)
        else:
            print(f"Warning : '{chunk_name_str}' not defined")

    def _create_chunk(self, chunk_type_bytes, chunk_data_bytes):
        length_bytes = struct.pack('>I', len(chunk_data_bytes))
        crc_input = chunk_type_bytes + chunk_data_bytes
        crc_val = zlib.crc32(crc_input) & 0xFFFFFFFF 
        crc_bytes = struct.pack('>I', crc_val)
        return length_bytes + chunk_type_bytes + chunk_data_bytes + crc_bytes

    def add_ihdr_chunk(self, validity_code):
        chunk_type = b'IHDR'
        current_color_type = self.color_type
        current_bit_depth = self.bit_depth
        current_width = self.width
        current_height = self.height

        if validity_code == 0: 
            comp, filt, inter = 0, 0, 0
        elif validity_code == 1: 
            current_width = 0 
            comp, filt, inter = 0, 0, 0
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for IHDR")
        
        valid_bit_depths_for_color_type = {
            0: [1, 2, 4, 8, 16], 2: [8, 16], 3: [1, 2, 4, 8],
            4: [8, 16], 6: [8, 16]
        }
        if current_bit_depth not in valid_bit_depths_for_color_type.get(current_color_type, []):
            current_bit_depth = valid_bit_depths_for_color_type.get(current_color_type, [8])[0]

        self.width, self.height, self.bit_depth, self.color_type = current_width, current_height, current_bit_depth, current_color_type
        
        chunk_data = struct.pack('>IIBBBBB', self.width, self.height, self.bit_depth, self.color_type, comp, filt, inter)
        self.data += self._create_chunk(chunk_type, chunk_data)

    def add_plte_chunk(self, validity_code):
        chunk_type = b'PLTE'
        chunk_data = b'' 
        actual_num_entries = 0

        if validity_code == 0:
            if self.color_type == 3:
                actual_num_entries = self.num_plte_entries
                if actual_num_entries == 0: 
                    actual_num_entries = 1
                    self.num_plte_entries = 1
            elif self.plte_chunk_present: 
                 actual_num_entries = random.randint(1, 256)
                 self.num_plte_entries = actual_num_entries 
            else: 
                self.plte_chunk_present = False 
                self.num_plte_entries = 0
                return 

            for _ in range(actual_num_entries): 
                chunk_data += bytes([random.randint(0,255), random.randint(0,255), random.randint(0,255)])
            
            if actual_num_entries > 0:
                self.plte_chunk_present = True 
            else: 
                self.plte_chunk_present = False
                return
                 
        elif validity_code == 1: 
            chunk_data = b'\x00\x00\x00\xFF' 
            self.plte_chunk_present = True 
            self.num_plte_entries = 1 
        else: 
            self.plte_chunk_present = False
            self.num_plte_entries = 0
            return
        
        if chunk_data or validity_code == 1:
             self.data += self._create_chunk(chunk_type, chunk_data)
        elif not chunk_data and validity_code == 0 and actual_num_entries == 0:
            pass


    def add_time_chunk(self, validity_code):
        chunk_type = b'tIME'
        chunk_data = None
        if validity_code == 0: 
            now = datetime.datetime.utcnow()
            chunk_data = struct.pack('>HBBBBB', now.year, now.month, now.day, now.hour, now.minute, now.second)
        elif validity_code == 1: 
            chunk_data = struct.pack('>HBBBBB', 2023, 13, 32, 25, 61, 62) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for tIME")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_trns_chunk(self, validity_code):
        chunk_type = b'tRNS'
        chunk_data = None
        if self.color_type == 4 or self.color_type == 6:
            return

        if validity_code == 0: 
            if self.color_type == 0: 
                gray_transparent_sample = random.randint(0, (1 << self.bit_depth) -1 if self.bit_depth <= 16 else 255)
                chunk_data = struct.pack('>H', gray_transparent_sample)
            elif self.color_type == 2: 
                max_val = (1 << self.bit_depth) -1 if self.bit_depth else 255
                r_trans, g_trans, b_trans = random.randint(0,max_val), random.randint(0,max_val), random.randint(0,max_val)
                chunk_data = struct.pack('>HHH', r_trans, g_trans, b_trans)
            elif self.color_type == 3: 
                if not self.plte_chunk_present or self.num_plte_entries == 0:
                    return
                num_alpha_entries = random.randint(0, self.num_plte_entries)
                alpha_values = [random.randint(0,255) for _ in range(num_alpha_entries)]
                chunk_data = bytes(alpha_values)
            else: 
                return
        elif validity_code == 1: 
            if self.color_type == 0:
                chunk_data = b'\x00' 
            elif self.color_type == 2:
                chunk_data = b'\x00\x00\x00\x00\x00' 
            elif self.color_type == 3:
                if self.plte_chunk_present and self.num_plte_entries > 0:
                    chunk_data = bytes([255] * (self.num_plte_entries + 1))
                else: 
                    chunk_data = b'\x00\x01\x02' 
            else: 
                return
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for tRNS")

        if chunk_data is not None: 
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_ztxt_chunk(self, validity_code):
        chunk_type = b'zTXt'
        chunk_data = None
        if validity_code == 0: 
            keyword = b"Software" 
            null_separator = b'\x00'
            compression_method = b'\x00' 
            original_text = b"Generated by PNGClass v1.0 (Latin-1)"
            compressed_text = zlib.compress(original_text)
            chunk_data = keyword + null_separator + compression_method + compressed_text
        elif validity_code == 1: 
            keyword = b"InvalidZtxt"
            null_separator = b'\x00'
            compression_method = b'\x01' 
            compressed_text = zlib.compress(b"some data")
            chunk_data = keyword + null_separator + compression_method + compressed_text
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for zTXt")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_srgb_chunk(self, validity_code):
        chunk_type = b'sRGB'
        chunk_data = None
        if validity_code == 0: 
            rendering_intent = random.choice([0,1,2,3])
            chunk_data = struct.pack('>B', rendering_intent)
        elif validity_code == 1: 
            chunk_data = struct.pack('>BB', 0, 0) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for sRGB")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_ster_chunk(self, validity_code):
        chunk_type = b'sTER'
        chunk_data = None
        if validity_code == 0: 
            mode = random.choice([0,1]) 
            chunk_data = struct.pack('>B', mode)
        elif validity_code == 1: 
            chunk_data = struct.pack('>BB', 0, 0) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for sTER")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_text_chunk(self, validity_code):
        chunk_type = b'tEXt'
        chunk_data = None
        if validity_code == 0: 
            keywords = [b"Title", b"Author", b"Description", b"Copyright", b"Creation Time", b"Software", b"Disclaimer", b"Warning", b"Source", b"Comment"]
            keyword = random.choice(keywords)
            null_separator = b'\x00'
            text_string = f"Sample {keyword.decode('latin-1')} text (Latin-1). Random number: {random.randint(1,1000)}".encode('latin-1')
            chunk_data = keyword + null_separator + text_string
        elif validity_code == 1: 
            keyword = b"A" * 80 
            null_separator = b'\x00'
            text_string = b"Illegal keyword."
            chunk_data = keyword + null_separator + text_string
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for tEXt")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_phys_chunk(self, validity_code):
        chunk_type = b'pHYs'
        chunk_data = None
        if validity_code == 0: 
            pixels_per_unit_x = random.randint(1, 10000) 
            pixels_per_unit_y = random.randint(1, 10000)
            unit_specifier = random.choice([0,1]) 
            chunk_data = struct.pack('>IIB', pixels_per_unit_x, pixels_per_unit_y, unit_specifier)
        elif validity_code == 1: 
            chunk_data = struct.pack('>II', 2835, 2835) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for pHYs")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_sbit_chunk(self, validity_code):
        chunk_type = b'sBIT'
        chunk_data = None
        max_sb = self.bit_depth
        if self.color_type == 3: 
            max_sb_palette = 8
        
        sb_gray = random.randint(1, max_sb)
        sb_red = random.randint(1, max_sb_palette if self.color_type == 3 else max_sb)
        sb_green = random.randint(1, max_sb_palette if self.color_type == 3 else max_sb)
        sb_blue = random.randint(1, max_sb_palette if self.color_type == 3 else max_sb)
        sb_alpha = random.randint(1, max_sb)

        if validity_code == 0: 
            if self.color_type == 0: 
                chunk_data = struct.pack('>B', sb_gray)
            elif self.color_type == 2: 
                chunk_data = struct.pack('>BBB', sb_red, sb_green, sb_blue)
            elif self.color_type == 3: 
                chunk_data = struct.pack('>BBB', sb_red, sb_green, sb_blue) 
            elif self.color_type == 4: 
                chunk_data = struct.pack('>BB', sb_gray, sb_alpha)
            elif self.color_type == 6: 
                chunk_data = struct.pack('>BBBB', sb_red, sb_green, sb_blue, sb_alpha)
            else: 
                return
        elif validity_code == 1: 
            if self.color_type == 0: chunk_data = b'\x08\x08' 
            elif self.color_type == 2: chunk_data = b'\x08\x08' 
            elif self.color_type == 3: chunk_data = b'\x08\x08' 
            elif self.color_type == 4: chunk_data = b'\x08' 
            elif self.color_type == 6: chunk_data = b'\x08\x08\x08' 
            else: chunk_data = b'invalid_sbit' 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for sBIT")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_splt_chunk(self, validity_code):
        chunk_type = b'sPLT'
        chunk_data = None
        if validity_code == 0: 
            palette_name = f"RandPalette{random.randint(1,100)}".encode('latin-1')[:79]
            null_separator = b'\x00'
            sample_depth_splt = random.choice([8, 16])
            entries_data = b''
            num_splt_entries = random.randint(1, 10) 
            if sample_depth_splt == 8:
                for _ in range(num_splt_entries):
                    r, g, b, a = random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255)
                    frequency = random.randint(0, 65535)
                    entries_data += struct.pack('>BBBBH', r, g, b, a, frequency)
            elif sample_depth_splt == 16:
                 for _ in range(num_splt_entries):
                    r,g,b,a = random.randint(0,65535),random.randint(0,65535),random.randint(0,65535),random.randint(0,65535)
                    frequency = random.randint(0, 65535)
                    entries_data += struct.pack('>HHHHH', r, g, b, a, frequency)
            chunk_data = palette_name + null_separator + bytes([sample_depth_splt]) + entries_data
        elif validity_code == 1: 
            palette_name = b"InvalidDepthPalette"
            null_separator = b'\x00'
            sample_depth_splt = 10 
            entries_data = b'\x00\x00\x00\x00\x00\x00' 
            chunk_data = palette_name + null_separator + bytes([sample_depth_splt]) + entries_data
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for sPLT")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_hist_chunk(self, validity_code):
        chunk_type = b'hIST'
        chunk_data = None
        if self.color_type != 3 or not self.plte_chunk_present or self.num_plte_entries == 0:
            return
        if validity_code == 0: 
            chunk_data = b''
            for _ in range(self.num_plte_entries):
                frequency = random.randint(0, 65535)
                chunk_data += struct.pack('>H', frequency) 
        elif validity_code == 1: 
            if self.num_plte_entries > 0:
                chunk_data = struct.pack('>H', random.randint(0, 65535)) * (self.num_plte_entries -1 if self.num_plte_entries > 1 else self.num_plte_entries + 1 if self.num_plte_entries > 0 else 2) 
            else: 
                chunk_data = b'\x00\x01\x00' 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for hIST")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_iccp_chunk(self, validity_code):
        chunk_type = b'iCCP'
        chunk_data = None
        if validity_code == 0: 
            profile_name = f"RandICCProfile{random.randint(1,100)}".encode('latin-1')[:79]
            null_separator = b'\x00'
            compression_method = b'\x00' 
            uncompressed_profile_data = f"This is a tiny fake ICC profile data {random.random()}".encode('latin-1')
            compressed_profile = zlib.compress(uncompressed_profile_data)
            chunk_data = profile_name + null_separator + compression_method + compressed_profile
        elif validity_code == 1: 
            profile_name = b"InvalidCMProfile"
            null_separator = b'\x00'
            compression_method = b'\x01' 
            compressed_profile = zlib.compress(b"some data")
            chunk_data = profile_name + null_separator + compression_method + compressed_profile
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for iCCP")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_itxt_chunk(self, validity_code):
        chunk_type = b'iTXt'
        chunk_data = None
        if validity_code == 0: 
            keywords = [b"Title", b"Author", b"Description", b"Copyright", b"Creation Time", b"Software", b"Disclaimer", b"Warning", b"Source", b"Comment"]
            keyword = random.choice(keywords)
            null_sep1 = b'\x00'
            compression_flag = random.choice([b'\x00', b'\x01']) 
            compression_method = b'\x00' 
            
            lang_tags = [b"en", b"en-US", b"fr-CA", b"ja", b""]
            language_tag = random.choice(lang_tags)
            null_sep2 = b'\x00'
            
            translated_keyword_text = f"{keyword.decode('latin-1')} ({language_tag.decode('latin-1') if language_tag else 'universal'})"
            translated_keyword = translated_keyword_text.encode('utf-8')[:79] 
            null_sep3 = b'\x00'
            
            text_content = f"UTF-8 text for {keyword.decode('latin-1')}: Some random international characters like éàçüö € and a number {random.randint(1,1000)}.".encode('utf-8')
            
            if compression_flag == b'\x01':
                text_to_process = zlib.compress(text_content)
            else:
                text_to_process = text_content
            
            chunk_data = keyword + null_sep1 + compression_flag + compression_method + \
                         language_tag + null_sep2 + translated_keyword + null_sep3 + text_to_process
        elif validity_code == 1: 
            keyword = b"InvalidNulls" 
            null_sep1 = b'\x00'
            compression_flag = b'\x00'
            compression_method = b'\x00'
            language_tag = b"xx"
            # null_sep2 is missing for this illegal case
            translated_keyword = b"InvKeyUTF8" # Corrected: No .encode() on bytes literal
            null_sep3 = b'\x00'
            text = b"Some text" # This is already bytes
            chunk_data = keyword + null_sep1 + compression_flag + compression_method + \
                         language_tag + translated_keyword + null_sep3 + text 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for iTXt")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_gama_chunk(self, validity_code):
        chunk_type = b'gAMA'
        chunk_data = None
        if validity_code == 0: 
            gamma_value_scaled = random.randint(50000, 300000) 
            chunk_data = struct.pack('>I', gamma_value_scaled) 
        elif validity_code == 1: 
            chunk_data = struct.pack('>H', 22000) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for gAMA")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_exif_chunk(self, validity_code):
        chunk_type = b'eXIf'
        chunk_data = None
        if validity_code == 0: 
            exif_header = b'Exif\x00\x00'
            tiff_structure = b'MM\x00\x2A\x00\x00\x00\x08\x00\x00' 
            chunk_data = exif_header + tiff_structure
        elif validity_code == 1: 
            chunk_data = b'NotValidExifDataTooShort' 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for eXIf")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_dsig_chunk(self, validity_code):
        chunk_type = b'dSIG'
        chunk_data = None
        if validity_code == 0: 
            chunk_data = bytes([random.randint(0,255) for _ in range(random.randint(16,128))])
        elif validity_code == 1: 
            chunk_data = b'' 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for dSIG")
        if chunk_data is not None: 
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_chrm_chunk(self, validity_code):
        chunk_type = b'cHRM'
        chunk_data = None
        if validity_code == 0: 
            values = [random.randint(0, 70000) for _ in range(8)] 
            chunk_data = struct.pack('>IIIIIIII', *values)
        elif validity_code == 1: 
            chunk_data = struct.pack('>IIIIIII', 31270, 32900, 64000, 33000, 30000, 60000, 15000) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for cHRM")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_cicp_chunk(self, validity_code):
        chunk_type = b'cICP'
        chunk_data = None
        if validity_code == 0: 
            colour_primaries = random.randint(1,12) 
            transfer_characteristics = random.randint(1,18) 
            matrix_coefficients = random.randint(0,12) 
            video_full_range_flag = random.choice([0,1]) 
            chunk_data = struct.pack('>BBBB', colour_primaries, transfer_characteristics, matrix_coefficients, video_full_range_flag)
        elif validity_code == 1: 
            chunk_data = struct.pack('>BBB', 1, 1, 1) 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for cICP")
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_bkgd_chunk(self, validity_code):
        chunk_type = b'bKGD'
        chunk_data = None 
        if self.color_type is None or self.bit_depth is None:
            return

        if validity_code == 0:  
            if self.color_type == 0 or self.color_type == 4:  
                max_val_bd = (1 << self.bit_depth) -1
                gray_sample = random.randint(0, max_val_bd)
                chunk_data = struct.pack('>H', gray_sample) 
            elif self.color_type == 2 or self.color_type == 6: 
                max_val_bd = (1 << self.bit_depth) -1
                red_sample = random.randint(0, max_val_bd)
                green_sample = random.randint(0, max_val_bd)
                blue_sample = random.randint(0, max_val_bd)
                chunk_data = struct.pack('>HHH', red_sample, green_sample, blue_sample) 
            elif self.color_type == 3: 
                if not self.plte_chunk_present or self.num_plte_entries == 0:
                    return
                palette_index = 0 
                if self.num_plte_entries > 0:
                    palette_index = random.randint(0, self.num_plte_entries - 1)
                chunk_data = struct.pack('>B', palette_index) 
            else:
                return
        elif validity_code == 1:  
            if self.color_type == 0 or self.color_type == 4: chunk_data = b'\x00'  
            elif self.color_type == 2 or self.color_type == 6: chunk_data = b'\x00\x00\x00\x00\x00' 
            elif self.color_type == 3: chunk_data = b'\x00\x00'  
            else: chunk_data = b'invalid_bkgd_data_generic'
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for bKGD")
        
        if chunk_data is not None: 
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_idat_chunk(self, validity_code):
        chunk_type = b'IDAT'
        chunk_data = None
        if validity_code == 0: 
            bytes_per_pixel_approx = 1
            if self.color_type == 0: 
                bytes_per_pixel_approx = (self.bit_depth + 7) // 8
            elif self.color_type == 2: 
                bytes_per_pixel_approx = 3 * ((self.bit_depth + 7) // 8)
            elif self.color_type == 3: 
                 pass 
            elif self.color_type == 4: 
                bytes_per_pixel_approx = 2 * ((self.bit_depth + 7) // 8)
            elif self.color_type == 6: 
                bytes_per_pixel_approx = 4 * ((self.bit_depth + 7) // 8)

            if self.color_type == 3 : 
                 scanline_payload_size = (self.width * self.bit_depth + 7) // 8
            else:
                 scanline_payload_size = self.width * bytes_per_pixel_approx
            
            if scanline_payload_size == 0 and self.width > 0 : 
                scanline_payload_size = 1

            raw_scanline_payload = b'\x00' * scanline_payload_size 
            
            uncompressed_image_data = b''
            for _ in range(self.height):
                uncompressed_image_data += b'\x00' 
                uncompressed_image_data += raw_scanline_payload
            
            if not uncompressed_image_data: 
                uncompressed_image_data = b'\x00' 

            try:
                chunk_data = zlib.compress(uncompressed_image_data)
            except AttributeError: 
                chunk_data = zlib.compress(uncompressed_image_data)
            except zlib.error as e:
                print(f"Zlib compression error for IDAT: {e}. Data: {uncompressed_image_data!r}")
                chunk_data = b"zlib_error_placeholder" 
        
        elif validity_code == 1: 
            chunk_data = b"This is not valid DEFLATE data for IDAT."
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for IDAT")
        
        if chunk_data is not None:
            self.data += self._create_chunk(chunk_type, chunk_data)

    def add_iend_chunk(self, validity_code):
        chunk_type = b'IEND'
        chunk_data = None
        if validity_code == 0:
            chunk_data = b''
        elif validity_code == 1:
            chunk_data = b'EOF_data_not_allowed' 
        else:
            raise ValueError(f"Unknown validity_code '{validity_code}' for IEND")
        
        if chunk_data is not None:
             self.data += self._create_chunk(chunk_type, chunk_data)

if __name__ == '__main__':
    critical_chunk_names = ['IHDR', 'PLTE', 'IDAT', 'IEND']
    ancillary_chunk_names = [
        'sBIT', 'gAMA', 'cHRM', 'sRGB', 'cICP', 'eXIf', 'iCCP', 'sPLT', 
        'hIST', 'tRNS', 'bKGD', 'pHYs', 'sTER', 'tEXt', 'zTXt', 'iTXt', 'tIME', 'dSIG' 
    ]
    parent_path = ''
    if len(sys.argv) > 1:
        parent_path = sys.argv[1]
    parent_path = f'{parent_path}/{randPNG_save_path}'
    # create directory to save seeds
    if not os.path.exists(parent_path):
        os.mkdir(parent_path)
        print(f'Creating directory {parent_path} to save random seeds')
    # remove files in the path if any
    for f in glob.glob(f'{parent_path}/*'):
        os.remove(f)
    print(f'Saving seeds to {parent_path}')
    for _ in range(10):
        random_crit_config = {name: random.choice([0, 1]) for name in critical_chunk_names}
        random_anc_config = {name: random.choice([0, 1, 2]) for name in ancillary_chunk_names}

        generated_png = PNG(critical_chunk_config=random_crit_config, ancillary_chunk_config=random_anc_config)

        output_filename = "randPNG_"+"".join(str(value) for value in random_crit_config.values())+"-"+"".join(str(value) for value in random_anc_config.values())+".png"
        try:
            with open(f'{parent_path}/{output_filename}', "wb") as f:
                f.write(generated_png.data)
            print(f"\nSave as '{output_filename}'")
        except IOError as e:
            print(f"\nFail to save '{output_filename}' {e}")
