cmake_minimum_required(VERSION 3.20)
project(Team10LinkLevelSimulation LANGUAGES CXX)

set(PROFESSOR_SOURCE_DIR "" CACHE PATH "Source directory of the prepared simulator copy")
if(NOT EXISTS "${PROFESSOR_SOURCE_DIR}/Modulation/QAMa/QAM32.cpp")
    message(FATAL_ERROR "Set PROFESSOR_SOURCE_DIR to the prepared simulator's Source directory")
endif()

add_executable(rectangular_experiment
    rectangular_experiment.cpp
    "${PROFESSOR_SOURCE_DIR}/Modulation/QAMa/QAM32.cpp"
    "${PROFESSOR_SOURCE_DIR}/Modulation/QAMa/QAMa.cpp"
    "${PROFESSOR_SOURCE_DIR}/Modulation/QAM/QAM.cpp"
    "${PROFESSOR_SOURCE_DIR}/Modulation/MaryModulation.cpp"
    "${PROFESSOR_SOURCE_DIR}/Library/Complex.cpp"
    "${PROFESSOR_SOURCE_DIR}/Library/Rand.cpp"
    "${PROFESSOR_SOURCE_DIR}/FileOutput/FileOutput.cpp"
)
target_include_directories(rectangular_experiment PRIVATE "${PROFESSOR_SOURCE_DIR}")
target_compile_features(rectangular_experiment PRIVATE cxx_std_17)
