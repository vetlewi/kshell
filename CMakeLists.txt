cmake_minimum_required(VERSION 3.18 FATAL_ERROR)


project(KShell 
    VERSION 2.0.0 
    LANGUAGES Fortran
)

include(GNUInstallDirs)


#---------- Search for dependencies ----------#
find_package(LAPACK REQUIRED)
find_package(BLAS REQUIRED)
find_package(OpenMP REQUIRED)

#---------- Define sources ----------#
set(sources
    ${CMAKE_CURRENT_SOURCE_DIR}/src/constant.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/model_space.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lib_matrix.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/class_stopwatch.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/partition.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wavefunction.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/rotation_group.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/harmonic_oscillator.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/operator_jscheme.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/operator_mscheme.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bridge_partitions.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/sp_matrix_element.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bp_io.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lanczos.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bp_expc_val.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bp_block.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/block_lanczos.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wavefunction.F90
    #${CMAKE_CURRENT_SOURCE_DIR}/src/bp_block_inc.F90
)

#---------- Define targets ----------#
add_library(kshell ${sources})
target_compile_options(kshell PRIVATE -fallow-argument-mismatch)
target_link_libraries(kshell PUBLIC OpenMP::OpenMP_Fortran LAPACK::LAPACK BLAS::BLAS)

add_executable(kshell.exe ${CMAKE_CURRENT_SOURCE_DIR}/src/kshell.F90)
target_link_libraries(kshell.exe PRIVATE kshell)

add_executable(transit.exe ${CMAKE_CURRENT_SOURCE_DIR}/src/transit.F90)
target_link_libraries(transit.exe PRIVATE kshell)

add_executable(count_dim.exe ${CMAKE_CURRENT_SOURCE_DIR}/src/count_dim.F90)
target_link_libraries(count_dim.exe PRIVATE kshell)


INSTALL(TARGETS kshell.exe transit.exe count_dim.exe RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})



