#pragma once
#include <mutex>

template<typename T>
class Singleton {
public:
    // 获取单例实例（延迟初始化，第一次调用时才创建实例）
    static T* inst() {
        std::call_once(_initFlag, create);
        return _instance;
    }
    
    // 提前初始化单例实例（在程序启动时就创建实例）
    static void preInit() {
        std::call_once(_initFlag, create);
    }

private:
    static void create() {
        _instance = new T();
    }

    static std::once_flag _initFlag;
    static T* _instance;
};

template<typename T>
std::once_flag Singleton<T>::_initFlag;

template<typename T>
T* Singleton<T>::_instance = nullptr;
