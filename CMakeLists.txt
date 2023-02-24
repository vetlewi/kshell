cmake_minimum_required(VERSION 3.18 FATAL_ERROR)


project(KShell 
    VERSION 2.0.0 
    LANGUAGES Fortran C
)

include(GNUInstallDirs)

option(BETZY "Build with flags ideal for Betzy" OFF)
if ( CMAKE_Fortran_COMPILER_ID MATCHES "^Intel")
    set(BLA_VENDOR Intel10_64lp)
endif()


#---------- Search for dependencies ----------#
find_package(MPI REQUIRED)
find_package(LAPACK REQUIRED)
find_package(BLAS REQUIRED)
find_package(OpenMP REQUIRED)

#---------- Define sources ----------#
set(sources
    ${CMAKE_CURRENT_SOURCE_DIR}/src/constant.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/model_space.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lib_matrix.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/class_stopwatch.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/partition.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wavefunction.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/rotation_group.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/harmonic_oscillator.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/operator_jscheme.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/operator_mscheme.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bridge_partitions.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/sp_matrix_element.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bp_io.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lanczos.f90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bp_expc_val.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/bp_block.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/block_lanczos.F90
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wavefunction.F90
)

#---------- Define targets ----------#
add_library(kshell ${sources})

if ( CMAKE_Fortran_COMPILER_ID STREQUAL "GNU" )
    target_compile_options(kshell PRIVATE -fallow-argument-mismatch)
endif()
if( BETZY AND MPI_FOUND )
    target_compile_definitions(kshell PUBLIC MPI)
    target_link_libraries(kshell PUBLIC OpenMP::OpenMP_Fortran LAPACK::LAPACK BLAS::BLAS MPI::MPI_Fortran)
else()
    target_link_libraries(kshell PUBLIC OpenMP::OpenMP_Fortran LAPACK::LAPACK BLAS::BLAS)
endif()

add_library(fakeintel SHARED ${CMAKE_CURRENT_SOURCE_DIR}/src/fakeintel.c)

add_executable(kshell.exe ${CMAKE_CURRENT_SOURCE_DIR}/src/kshell.F90)
target_link_libraries(kshell.exe PRIVATE kshell fakeintel)
if(UNIX AND NOT APPLE)
    add_custom_command(TARGET kshell.exe POST_BUILD
        COMMAND patchelf --add-needed libfakeintel.so kshell.exe
        COMMENT "Patching kshell.exe with fake Intel symbol")
endif()
add_custom_command(TARGET kshell.exe POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:kshell.exe> ${CMAKE_CURRENT_LIST_DIR}/bin
    COMMENT "Copied kshell.exe to bin dir"
)

add_executable(transit.exe ${CMAKE_CURRENT_SOURCE_DIR}/src/transit.F90)
target_link_libraries(transit.exe PRIVATE kshell)
add_custom_command(TARGET transit.exe POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:transit.exe> ${CMAKE_CURRENT_LIST_DIR}/bin
    COMMENT "Copied transit.exe to bin dir"
)

add_executable(count_dim.exe ${CMAKE_CURRENT_SOURCE_DIR}/src/count_dim.f90)
target_link_libraries(count_dim.exe PRIVATE kshell)
add_custom_command(TARGET count_dim.exe POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:count_dim.exe> ${CMAKE_CURRENT_LIST_DIR}/bin
    COMMENT "Copied count_dim.exe to bin dir"
)



