#pragma once
#include <cstdlib>
#include <string>

#ifndef VAR_ENV
#define VAR_ENV "DLT645_ROOT"
#endif

#ifndef DEFAULT_ROOT_DIR
#define DEFAULT_ROOT_DIR "."
#endif

inline std::string rootPath()
{
#ifdef _MSC_VER
  char *envRoot = nullptr;
  size_t length = 0;
  if (_dupenv_s(&envRoot, &length, VAR_ENV) != 0 || envRoot == nullptr)
  {
    return DEFAULT_ROOT_DIR;
  }
  std::string rootDir(envRoot);
  std::free(envRoot);
  return rootDir;
#else
  std::string rootDir;
  const char *envRoot = std::getenv(VAR_ENV);
  if (nullptr == envRoot)
  {
    rootDir = DEFAULT_ROOT_DIR;
  }
  else
  {
    rootDir = envRoot;
  }

  return rootDir;
#endif
}

inline std::string logPath() { return rootPath() + "/log/"; }
