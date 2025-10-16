#pragma once
#include <cstdlib>
#include <fstream>
#include <string>

#ifndef VAR_ENV
#define VAR_ENV "DLT645_ROOT"
#endif

#ifndef DEFAULT_ROOT_DIR
#define DEFAULT_ROOT_DIR "/home/narada/dlt645/cpp/build"
#endif

inline std::string rootPath() {
  std::string rootDir;
  const char *envRoot = getenv(VAR_ENV);
  if (nullptr == envRoot) {
    rootDir = DEFAULT_ROOT_DIR;
  } else {
    rootDir = envRoot;
  }

  return rootDir;
}

inline std::string confBasePath() { return rootPath() + "/config"; }

inline std::string dataPath() { return confBasePath() + "/data/"; }

inline std::string libPath() { return rootPath() + "/lib/"; }

inline std::string logPath() { return rootPath() + "/log/"; }