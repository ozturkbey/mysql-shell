/*
 * Copyright (c) 2018, 2020, Oracle and/or its affiliates. All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License, version 2.0,
 * as published by the Free Software Foundation.
 *
 * This program is also distributed with certain software (including
 * but not limited to OpenSSL) that is licensed under separate terms, as
 * designated in a particular file or component or in included license
 * documentation.  The authors of MySQL hereby grant you an additional
 * permission to link the program and your derivative works with the
 * separately licensed software that they have included with MySQL.
 * This program is distributed in the hope that it will be useful,  but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
 * the GNU General Public License, version 2.0, for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 */

#ifndef MODULES_UTIL_IMPORT_TABLE_IMPORT_TABLE_OPTIONS_H_
#define MODULES_UTIL_IMPORT_TABLE_IMPORT_TABLE_OPTIONS_H_

#ifdef _WIN32
#include <io.h>
#else
#include <unistd.h>
#endif

#include <memory>
#include <string>
#include <vector>
#include "modules/util/import_table/dialect.h"
#include "mysqlshdk/libs/db/connection_options.h"
#include "mysqlshdk/libs/db/mysql/session.h"
#include "mysqlshdk/libs/oci/oci_options.h"
#include "mysqlshdk/libs/storage/ifile.h"

namespace mysqlsh {
namespace import_table {

using Connection_options = mysqlshdk::db::Connection_options;

class Import_table_options {
 public:
  Import_table_options() = default;

  explicit Import_table_options(const shcore::Dictionary_t &options);

  Import_table_options(const std::string &filename,
                       const shcore::Dictionary_t &options);

  Import_table_options(const Import_table_options &other) = delete;
  Import_table_options(Import_table_options &&other) = default;

  Import_table_options &operator=(const Import_table_options &other) = delete;
  Import_table_options &operator=(Import_table_options &&other) = default;
  ~Import_table_options() = default;

  Dialect dialect() const { return m_dialect; }

  void validate();

  void base_session(
      const std::shared_ptr<mysqlshdk::db::mysql::Session> &session) {
    m_base_session = session;
  }

  Connection_options connection_options() const;

  const std::string &filename() const { return m_filename; }

  const std::string &full_path() const { return m_full_path; }

  size_t max_rate() const;

  bool replace_duplicates() const { return m_replace_duplicates; }

  void set_replace_duplicates(bool flag) { m_replace_duplicates = flag; }

  const std::vector<std::string> &columns() const { return m_columns; }

  const std::map<std::string, std::string> &decode_columns() const {
    return m_decode_columns;
  }

  bool show_progress() const { return m_show_progress; }

  uint64_t skip_rows_count() const { return m_skip_rows_count; }

  int64_t threads_size() const { return m_threads_size; }

  const std::string &table() const { return m_table; }

  const std::string &schema() const { return m_schema; }

  const std::string &character_set() const { return m_character_set; }

  size_t file_size() const { return m_file_size; }

  size_t bytes_per_chunk() const;

  std::string target_import_info() const;

  mysqlshdk::oci::Oci_options get_oci_options() const { return m_oci_options; }

  /**
   * Returns the raw pointer to the file handle
   */
  mysqlshdk::storage::IFile *file_handle() const { return m_file_handle.get(); }

  /**
   * Creates a new file handle using the provided options.
   */
  std::unique_ptr<mysqlshdk::storage::IFile> create_file_handle() const;

 private:
  void unpack(const shcore::Dictionary_t &options);

  size_t calc_thread_size();

  std::string m_filename;
  std::string m_full_path;
  size_t m_file_size;
  std::string m_table;
  std::string m_schema;
  std::string m_character_set;
  int64_t m_threads_size = 8;
  std::string m_bytes_per_chunk{"50M"};
  std::vector<std::string> m_columns;
  std::map<std::string, std::string> m_decode_columns;
  bool m_replace_duplicates = false;
  std::string m_max_rate;
  bool m_show_progress = isatty(fileno(stdout)) ? true : false;
  uint64_t m_skip_rows_count = 0;
  Dialect m_dialect;
  mysqlshdk::oci::Oci_options m_oci_options;
  std::shared_ptr<mysqlshdk::db::mysql::Session> m_base_session;
  std::unique_ptr<mysqlshdk::storage::IFile> m_file_handle;
};

}  // namespace import_table
}  // namespace mysqlsh

#endif  // MODULES_UTIL_IMPORT_TABLE_IMPORT_TABLE_OPTIONS_H_
