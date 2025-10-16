#pragma once
#include "rapidjson/document.h"
#include "rapidjson/pointer.h"
#include "rapidjson/prettywriter.h"
#include "rapidjson/stringbuffer.h"
#include <fstream>
#include <string>

using JsonDoc = rapidjson::Document;
using JsonObj = rapidjson::Value;
using JsonVal = rapidjson::Value;
using JsonPtr = rapidjson::Pointer;

inline bool parseJsonDoc(const std::string &jsonFile, JsonDoc &jsonDoc) {
  bool ret = false;
  do {
    std::ifstream in(jsonFile);
    if (!in.is_open()) {
      break;
    }

    std::string jsonContent((std::istreambuf_iterator<char>(in)),
                            std::istreambuf_iterator<char>());
    in.close();

    if (jsonDoc.Parse(jsonContent.c_str()).HasParseError()) {
      break;
    }
    ret = true;
  } while (0);

  return ret;
}

inline bool parseJsonContent(const std::string &jsonContent, JsonDoc &jsonDoc) {
  if (jsonDoc.Parse(jsonContent.c_str()).HasParseError()) {
    return false;
  }

  return true;
}

inline bool getJsonBoolVal(const JsonDoc &jsonDoc,
                           const std::string &strPointer, bool &outVal) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsBool()) {
    outVal = v->GetBool();
    return true;
  } else {
    return false;
  }
}

inline bool getJsonIntVal(const JsonDoc &jsonDoc, const std::string &strPointer,
                          int &outVal) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsInt()) {
    outVal = v->GetInt();
    return true;
  } else {
    return false;
  }
}

inline bool getJsonFloatVal(const JsonDoc &jsonDoc,
                            const std::string &strPointer, float &outVal) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsNumber()) {
    outVal = v->GetFloat();
    return true;
  } else {
    return false;
  }
}

inline bool getJsonDoubleVal(const JsonDoc &jsonDoc,
                             const std::string &strPointer, double &outVal) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsLosslessDouble()) {
    outVal = v->GetDouble();
    return true;
  } else {
    return false;
  }
}

inline bool getJsonStringVal(const JsonDoc &jsonDoc,
                             const std::string &strPointer,
                             std::string &outVal) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsString()) {
    outVal = v->GetString();
    return true;
  } else {
    return false;
  }
}

inline bool getJsonUIntVal(const JsonDoc &jsonDoc,
                           const std::string &strPointer,
                           unsigned int &outVal) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsUint()) {
    outVal = v->GetUint();
    return true;
  } else {
    return false;
  }
}

inline bool getArrayObj(JsonDoc &jsonDoc, const std::string &strPointer,
                        JsonObj &outArr) {
  const rapidjson::Value *v =
      rapidjson::Pointer(strPointer.c_str()).Get(jsonDoc);
  if (v != nullptr && v->IsArray()) {
    outArr = const_cast<rapidjson::Value &>(*v).Move();
    return true;
  } else {
    return false;
  }
}

inline bool getBoolFromJsonObj(const JsonObj &obj, const std::string &key,
                               bool &outVal) {
  if (!obj.HasMember(key.c_str()))
    return false;

  const rapidjson::Value &v = obj[key.c_str()];
  if (v.IsBool()) {
    outVal = v.GetBool();
    return true;
  } else {
    return false;
  }
}

inline bool getIntFromJsonObj(const JsonObj &obj, const std::string &key,
                              int &outVal) {
  if (!obj.HasMember(key.c_str()))
    return false;

  const rapidjson::Value &v = obj[key.c_str()];
  if (v.IsInt()) {
    outVal = v.GetInt();
    return true;
  } else {
    return false;
  }
}

inline bool getUintFromJsonObj(const JsonObj &obj, const std::string &key,
                               unsigned int &outVal) {
  if (!obj.HasMember(key.c_str()))
    return false;

  const rapidjson::Value &v = obj[key.c_str()];
  if (v.IsUint()) {
    outVal = v.GetUint();
    return true;
  } else {
    return false;
  }
}

inline bool getFloatFromJsonObj(const JsonObj &obj, const std::string &key,
                                float &outVal) {
  if (!obj.HasMember(key.c_str()))
    return false;

  const rapidjson::Value &v = obj[key.c_str()];
  if (v.IsLosslessFloat()) {
    outVal = v.GetFloat();
    return true;
  } else {
    return false;
  }
}

inline bool getDoubleFromJsonObj(const JsonObj &obj, const std::string &key,
                                 double &outVal) {
  if (!obj.HasMember(key.c_str()))
    return false;

  const rapidjson::Value &v = obj[key.c_str()];
  if (v.IsLosslessDouble()) {
    outVal = v.GetDouble();
    return true;
  } else {
    return false;
  }
}

inline bool getStringFromJsonObj(const JsonObj &obj, const std::string &key,
                                 std::string &outVal) {
  if (!obj.HasMember(key.c_str()))
    return false;

  const rapidjson::Value &v = obj[key.c_str()];
  if (v.IsString()) {
    outVal = v.GetString();
    return true;
  } else {
    return false;
  }
}

inline bool prettyWriteJsonDoc(const JsonDoc &jsonDoc, std::string &outJson) {
  rapidjson::StringBuffer buffer;
  rapidjson::PrettyWriter<rapidjson::StringBuffer> writer(buffer);
  if (!jsonDoc.Accept(writer)) {
    return false;
  }
  outJson = buffer.GetString();
  return true;
}