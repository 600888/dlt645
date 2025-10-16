
#include "dlt645/model/model.h"

namespace dlt645 {
namespace model {

bool isValueValid(const std::string &dataFormat, float value) {
  if (dataFormat == DataFormat::XXXXXX_XX) {
    return -799999.99 <= value && value <= 799999.99;
  } else if (dataFormat == DataFormat::XXXX_XX) {
    return -7999.99 <= value && value <= 7999.99;
  } else if (dataFormat == DataFormat::XXX_XXX) {
    return -799.999 <= value && value <= 799.999;
  }else if (dataFormat == DataFormat::XXX_X) {
    return -799.9 <= value && value <= 799.9;
  }else if(dataFormat == DataFormat::XX_XXXX){
    return -79.9999 <= value && value <= 79.9999;
  }else if (dataFormat == DataFormat::XX_XX) {
    return -79.99 <= value && value <= 79.99;
  }else if (dataFormat == DataFormat::X_XXX) {
    return -7.999 <= value && value <= 7.999;
  }
  return false;
}

} // namespace model
} // namespace dlt645