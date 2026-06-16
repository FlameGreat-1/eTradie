54s
Run docker/build-push-action@v6
GitHub Actions runtime token ACs
Docker info
Proxy configuration
Buildx version
Builder info
/usr/bin/docker buildx build --build-arg MT5_INSTALLER_SHA256= --build-arg MT4_INSTALLER_SHA256= --build-arg MT5_INSTALLER_URL= --build-arg MT4_INSTALLER_URL= --build-arg EA_EX5_SHA256= --build-arg EA_EX4_SHA256= --build-arg WINEHQ_VERSION= --cache-from type=gha,scope=engine --cache-to type=gha,mode=max,scope=engine --file Dockerfile --iidfile /home/runner/work/_temp/docker-actions-toolkit-jHLv7I/build-iidfile-6f95cc2947.txt --attest type=provenance,builder-id=https://github.com/FlameGreat-1/eTradie/actions/runs/27635610287/attempts/1 --attest type=sbom,disabled=false --tag ghcr.io/flamegreat-1/etradie/engine:77b805080b4baca35bacc0104ce7bba0f10e5ee0 --tag ghcr.io/flamegreat-1/etradie/engine:0.1.0 --tag ghcr.io/flamegreat-1/etradie/engine:staging-0.1.0 --metadata-file /home/runner/work/_temp/docker-actions-toolkit-jHLv7I/build-metadata-eb1f5ff2af.json .
#0 building with "builder-ef367e57-5794-4671-b1e4-64bf24a1a4be" instance using docker-container driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 6.12kB done
#1 DONE 0.0s

#2 [auth] docker/buildkit-syft-scanner:pull token for registry-1.docker.io
#2 DONE 0.0s

#3 resolve image config for docker-image://docker.io/docker/buildkit-syft-scanner:stable-1
#3 DONE 0.5s

#4 [auth] library/python:pull token for registry-1.docker.io
#4 DONE 0.0s

#5 [internal] load metadata for docker.io/library/python:3.14-slim
#5 DONE 0.4s

#6 [internal] load .dockerignore
#6 transferring context: 1.16kB done
#6 DONE 0.0s

#7 [internal] load build context
#7 DONE 0.0s

#8 [builder 1/8] FROM docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061
#8 resolve docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061 0.0s done
#8 DONE 0.0s

#9 docker-image://docker.io/docker/buildkit-syft-scanner:stable-1
#9 resolve docker.io/docker/buildkit-syft-scanner:stable-1 0.1s done
#9 DONE 0.1s

#10 importing cache manifest from gha:14074510552613513460
#10 DONE 0.2s

#8 [builder 1/8] FROM docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061
#8 sha256:29834f362f6707ca7d7b3dab84940835bc605366abd298c8eb80c1aea11d52b7 249B / 249B 0.1s done
#8 sha256:af30767b7cec62d8fced706f16261691936a306b774196f12d43681755f483d3 12.34MB / 12.34MB 0.2s done
#8 sha256:72c03230f1363a3fb61d2f98504cf168bad3fe22f511ad2005dc021515d7ce97 4.19MB / 29.79MB 0.2s
#8 sha256:da106fed7af036778f0d10708e3f8a6dd3efcfac5c3ac7ad6f5df982a0fbfbc9 1.29MB / 1.29MB 0.1s done
#8 sha256:72c03230f1363a3fb61d2f98504cf168bad3fe22f511ad2005dc021515d7ce97 23.07MB / 29.79MB 0.3s
#8 ...

#7 [internal] load build context
#7 transferring context: 6.60MB 0.2s done
#7 DONE 0.6s

#8 [builder 1/8] FROM docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061
#8 sha256:72c03230f1363a3fb61d2f98504cf168bad3fe22f511ad2005dc021515d7ce97 29.79MB / 29.79MB 0.5s
#8 sha256:72c03230f1363a3fb61d2f98504cf168bad3fe22f511ad2005dc021515d7ce97 29.79MB / 29.79MB 0.6s done
#8 extracting sha256:72c03230f1363a3fb61d2f98504cf168bad3fe22f511ad2005dc021515d7ce97
#8 ...

#9 docker-image://docker.io/docker/buildkit-syft-scanner:stable-1
#9 sha256:8b29db3a8efc45d6eea600012e1fed5a2452fc59a5b7e703a3e643ccbf5d4509 46.45MB / 46.45MB 0.6s done
#9 extracting sha256:8b29db3a8efc45d6eea600012e1fed5a2452fc59a5b7e703a3e643ccbf5d4509 0.4s done
#9 DONE 1.1s

#8 [builder 1/8] FROM docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061
#8 extracting sha256:72c03230f1363a3fb61d2f98504cf168bad3fe22f511ad2005dc021515d7ce97 0.6s done
#8 DONE 1.2s

#8 [builder 1/8] FROM docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061
#8 extracting sha256:da106fed7af036778f0d10708e3f8a6dd3efcfac5c3ac7ad6f5df982a0fbfbc9 0.1s done
#8 extracting sha256:af30767b7cec62d8fced706f16261691936a306b774196f12d43681755f483d3
#8 extracting sha256:af30767b7cec62d8fced706f16261691936a306b774196f12d43681755f483d3 0.3s done
#8 DONE 1.6s

#8 [builder 1/8] FROM docker.io/library/python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061
#8 extracting sha256:29834f362f6707ca7d7b3dab84940835bc605366abd298c8eb80c1aea11d52b7 done
#8 DONE 1.6s

#11 [runtime 2/9] RUN groupadd --gid 1000 etradie     && useradd --uid 1000 --gid etradie --shell /bin/bash --create-home etradie
#11 ...

#12 [builder 2/8] WORKDIR /build
#12 DONE 1.4s

#11 [runtime 2/9] RUN groupadd --gid 1000 etradie     && useradd --uid 1000 --gid etradie --shell /bin/bash --create-home etradie
#11 DONE 1.4s

#13 [builder 3/8] COPY requirements/base.txt requirements/base.txt
#13 DONE 0.0s

#14 [builder 4/8] RUN --mount=type=cache,target=/root/.cache/pip     pip install --default-timeout=1000 --retries=10 --prefix=/install         --extra-index-url https://download.pytorch.org/whl/cpu         -r requirements/base.txt
#14 1.590 Looking in indexes: https://pypi.org/simple, https://download.pytorch.org/whl/cpu
#14 1.802 Collecting fastapi>=0.115.8 (from -r requirements/base.txt (line 2))
#14 1.826   Downloading fastapi-0.137.1-py3-none-any.whl.metadata (26 kB)
#14 1.942 Collecting uvicorn==0.34.0 (from uvicorn[standard]==0.34.0->-r requirements/base.txt (line 3))
#14 1.945   Downloading uvicorn-0.34.0-py3-none-any.whl.metadata (6.5 kB)
#14 2.049 Collecting pydantic==2.9.2 (from -r requirements/base.txt (line 4))
#14 2.052   Downloading pydantic-2.9.2-py3-none-any.whl.metadata (149 kB)
#14 2.129 Collecting pydantic-settings==2.8.1 (from -r requirements/base.txt (line 5))
#14 2.132   Downloading pydantic_settings-2.8.1-py3-none-any.whl.metadata (3.5 kB)
#14 2.336 Collecting sqlalchemy==2.0.38 (from sqlalchemy[asyncio]==2.0.38->-r requirements/base.txt (line 8))
#14 2.341   Downloading SQLAlchemy-2.0.38-py3-none-any.whl.metadata (9.6 kB)
#14 2.432 Collecting asyncpg==0.30.0 (from -r requirements/base.txt (line 9))
#14 2.435   Downloading asyncpg-0.30.0.tar.gz (957 kB)
#14 2.454      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 957.7/957.7 kB 56.1 MB/s  0:00:00
#14 2.508   Installing build dependencies: started
#14 3.633   Installing build dependencies: finished with status 'done'
#14 3.634   Getting requirements to build wheel: started
#14 4.190   Getting requirements to build wheel: finished with status 'done'
#14 4.191   Preparing metadata (pyproject.toml): started
#14 4.407   Preparing metadata (pyproject.toml): finished with status 'done'
#14 4.454 Collecting alembic==1.14.1 (from -r requirements/base.txt (line 10))
#14 4.458   Downloading alembic-1.14.1-py3-none-any.whl.metadata (7.4 kB)
#14 4.572 Collecting greenlet==3.1.1 (from -r requirements/base.txt (line 11))
#14 4.576   Downloading greenlet-3.1.1.tar.gz (186 kB)
#14 4.606   Installing build dependencies: started
#14 5.319   Installing build dependencies: finished with status 'done'
#14 5.320   Getting requirements to build wheel: started
#14 5.633   Getting requirements to build wheel: finished with status 'done'
#14 5.634   Preparing metadata (pyproject.toml): started
#14 5.809   Preparing metadata (pyproject.toml): finished with status 'done'
#14 5.869 Collecting redis==5.2.1 (from redis[hiredis]==5.2.1->-r requirements/base.txt (line 14))
#14 5.872   Downloading redis-5.2.1-py3-none-any.whl.metadata (9.1 kB)
#14 6.227 Collecting aiohttp==3.14.1 (from -r requirements/base.txt (line 21))
#14 6.230   Downloading aiohttp-3.14.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (8.3 kB)
#14 6.285 Collecting aiohttp-retry==2.9.1 (from -r requirements/base.txt (line 22))
#14 6.288   Downloading aiohttp_retry-2.9.1-py3-none-any.whl.metadata (8.8 kB)
#14 6.332 Collecting feedparser==6.0.11 (from -r requirements/base.txt (line 25))
#14 6.336   Downloading feedparser-6.0.11-py3-none-any.whl.metadata (2.4 kB)
#14 6.377 Collecting APScheduler==3.10.4 (from -r requirements/base.txt (line 28))
#14 6.380   Downloading APScheduler-3.10.4-py3-none-any.whl.metadata (5.7 kB)
#14 6.431 Collecting prometheus-client==0.21.1 (from -r requirements/base.txt (line 31))
#14 6.434   Downloading prometheus_client-0.21.1-py3-none-any.whl.metadata (1.8 kB)
#14 6.493 Collecting opentelemetry-api==1.34.1 (from -r requirements/base.txt (line 41))
#14 6.496   Downloading opentelemetry_api-1.34.1-py3-none-any.whl.metadata (1.5 kB)
#14 6.541 Collecting opentelemetry-sdk==1.34.1 (from -r requirements/base.txt (line 42))
#14 6.544   Downloading opentelemetry_sdk-1.34.1-py3-none-any.whl.metadata (1.6 kB)


uild/lib.linux-x86_64-cpython-314/greenlet/platform
#14 43.27       copying src/greenlet/platform/switch_x86_msvc.h -> build/lib.linux-x86_64-cpython-314/greenlet/platform
#14 43.27       copying src/greenlet/platform/switch_x86_unix.h -> build/lib.linux-x86_64-cpython-314/greenlet/platform
#14 43.27       copying src/greenlet/tests/_test_extension.c -> build/lib.linux-x86_64-cpython-314/greenlet/tests
#14 43.27       copying src/greenlet/tests/_test_extension_cpp.cpp -> build/lib.linux-x86_64-cpython-314/greenlet/tests
#14 43.27       running build_ext
#14 43.27       building 'greenlet._greenlet' extension
#14 43.27       creating build/temp.linux-x86_64-cpython-314/src/greenlet
#14 43.27       gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -I/usr/local/include/python3.14 -c src/greenlet/greenlet.cpp -o build/temp.linux-x86_64-cpython-314/src/greenlet/greenlet.o
#14 43.27       error: command 'gcc' failed: No such file or directory
#14 43.27       [end of output]
#14 43.27   
#14 43.27   note: This error originates from a subprocess, and is likely not a problem with pip.
#14 43.27   ERROR: Failed building wheel for greenlet
#14 43.27   Building wheel for pyzmq (pyproject.toml): started
#14 43.52   Building wheel for pyzmq (pyproject.toml): finished with status 'error'
#14 43.52   error: subprocess-exited-with-error
#14 43.52   
#14 43.52   × Building wheel for pyzmq (pyproject.toml) did not run successfully.
#14 43.52   │ exit code: 1
#14 43.52   ╰─> [17 lines of output]
#14 43.52       WARNING: Use build.targets instead of cmake.targets for scikit-build-core >= 0.10
#14 43.52       *** scikit-build-core 0.12.2 using CMake 4.3.2 (wheel)
#14 43.52       *** Configuring CMake...
#14 43.52       loading initial cache file /tmp/tmpod1rrxla/build/CMakeInit.txt
#14 43.52       CMake Error at /tmp/pip-build-env-p8bhre0u/normal/lib/python3.14/site-packages/cmake/data/share/cmake-4.3/Modules/CMakeDetermineCCompiler.cmake:48 (message):
#14 43.52         Could not find the compiler specified in the environment variable CC:
#14 43.52       
#14 43.52         gcc.
#14 43.52       Call Stack (most recent call first):
#14 43.52         CMakeLists.txt:2 (project)
#14 43.52       
#14 43.52       
#14 43.52       CMake Error: CMAKE_C_COMPILER not set, after EnableLanguage
#14 43.52       CMake Error: CMAKE_CXX_COMPILER not set, after EnableLanguage
#14 43.52       -- Configuring incomplete, errors occurred!
#14 43.52       
#14 43.52       *** CMake configuration failed
#14 43.52       [end of output]
#14 43.52   
#14 43.52   note: This error originates from a subprocess, and is likely not a problem with pip.
#14 43.52   ERROR: Failed building wheel for pyzmq
#14 43.52   Building wheel for msgpack (pyproject.toml): started
#14 43.68   Building wheel for msgpack (pyproject.toml): finished with status 'error'
#14 43.69   error: subprocess-exited-with-error
#14 43.69   
#14 43.69   × Building wheel for msgpack (pyproject.toml) did not run successfully.
#14 43.69   │ exit code: 1
#14 43.69   ╰─> [53 lines of output]
#14 43.69       /tmp/pip-build-env-h2s8x_bb/overlay/lib/python3.14/site-packages/setuptools/config/_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated
#14 43.69       !!
#14 43.69       
#14 43.69               ********************************************************************************
#14 43.69               Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).
#14 43.69       
#14 43.69               By 2027-Feb-18, you need to update your project and remove deprecated calls
#14 43.69               or your builds will no longer be supported.
#14 43.69       
#14 43.69               See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
#14 43.69               ********************************************************************************
#14 43.69       
#14 43.69       !!
#14 43.69         corresp(dist, value, root_dir)
#14 43.69       /tmp/pip-build-env-h2s8x_bb/overlay/lib/python3.14/site-packages/setuptools/config/_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.
#14 43.69       !!
#14 43.69       
#14 43.69               ********************************************************************************
#14 43.69               Please consider removing the following classifiers in favor of a SPDX license expression:
#14 43.69       
#14 43.69               License :: OSI Approved :: Apache Software License
#14 43.69       
#14 43.69               See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
#14 43.69               ********************************************************************************
#14 43.69       
#14 43.69       !!
#14 43.69         dist._finalize_license_expression()
#14 43.69       /tmp/pip-build-env-h2s8x_bb/overlay/lib/python3.14/site-packages/setuptools/dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.
#14 43.69       !!
#14 43.69       
#14 43.69               ********************************************************************************
#14 43.69               Please consider removing the following classifiers in favor of a SPDX license expression:
#14 43.69       
#14 43.69               License :: OSI Approved :: Apache Software License
#14 43.69       
#14 43.69               See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
#14 43.69               ********************************************************************************
#14 43.69       
#14 43.69       !!
#14 43.69         self._finalize_license_expression()
#14 43.69       running bdist_wheel
#14 43.69       running build
#14 43.69       running build_py
#14 43.69       creating build/lib.linux-x86_64-cpython-314/msgpack
#14 43.69       copying msgpack/__init__.py -> build/lib.linux-x86_64-cpython-314/msgpack
#14 43.69       copying msgpack/exceptions.py -> build/lib.linux-x86_64-cpython-314/msgpack
#14 43.69       copying msgpack/fallback.py -> build/lib.linux-x86_64-cpython-314/msgpack
#14 43.69       copying msgpack/ext.py -> build/lib.linux-x86_64-cpython-314/msgpack
#14 43.69       running build_ext
#14 43.69       building 'msgpack._cmsgpack' extension
#14 43.69       creating build/temp.linux-x86_64-cpython-314/msgpack
#14 43.69       gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -I. -I/usr/local/include/python3.14 -c msgpack/_cmsgpack.c -o build/temp.linux-x86_64-cpython-314/msgpack/_cmsgpack.o
#14 43.69       error: command 'gcc' failed: No such file or directory
#14 43.69       [end of output]
#14 43.69   
#14 43.69   note: This error originates from a subprocess, and is likely not a problem with pip.
#14 43.69   ERROR: Failed building wheel for msgpack
#14 43.69   Building wheel for chroma-hnswlib (pyproject.toml): started
#14 43.91   Building wheel for chroma-hnswlib (pyproject.toml): finished with status 'error'
#14 43.91   error: subprocess-exited-with-error
#14 43.91   
#14 43.91   × Building wheel for chroma-hnswlib (pyproject.toml) did not run successfully.
#14 43.91   │ exit code: 1
#14 43.91   ╰─> [89 lines of output]
#14 43.91       running bdist_wheel
#14 43.91       running build
#14 43.91       running build_ext
#14 43.91       creating tmp
#14 43.91       gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -I/usr/local/include/python3.14 -c /tmp/tmpm5v7_6vs.cpp -o tmp/tmpm5v7_6vs.o -std=c++14
#14 43.91       gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -I/usr/local/include/python3.14 -c /tmp/tmppywi_hjx.cpp -o tmp/tmppywi_hjx.o -std=c++11
#14 43.91       Traceback (most recent call last):
#14 43.91         File "/usr/local/lib/python3.14/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 389, in <module>
#14 43.91           main()
#14 43.91           ~~~~^^
#14 43.91         File "/usr/local/lib/python3.14/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 373, in main
#14 43.91           json_out["return_val"] = hook(**hook_input["kwargs"])

el for chroma-hnswlib (pyproject.toml): started
#14 43.91   Building wheel for chroma-hnswlib (pyproject.toml): finished with status 'error'
#14 43.91   error: subprocess-exited-with-error
#14 43.91   
#14 43.91   × Building wheel for chroma-hnswlib (pyproject.toml) did not run successfully.
#14 43.91   │ exit code: 1
#14 43.91   ╰─> [89 lines of output]
#14 43.91       running bdist_wheel
#14 43.91       running build
#14 43.91       running build_ext
#14 43.91       creating tmp
#14 43.91       gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -I/usr/local/include/python3.14 -c /tmp/tmpm5v7_6vs.cpp -o tmp/tmpm5v7_6vs.o -std=c++14
#14 43.91       gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -I/usr/local/include/python3.14 -c /tmp/tmppywi_hjx.cpp -o tmp/tmppywi_hjx.o -std=c++11
#14 43.91       Traceback (most recent call last):
#14 43.91         File "/usr/local/lib/python3.14/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 389, in <module>
#14 43.91           main()
#14 43.91           ~~~~^^
#14 43.91         File "/usr/local/lib/python3.14/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 373, in main
#14 43.91           json_out["return_val"] = hook(**hook_input["kwargs"])
#14 43.91                                    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^
#14 43.91         File "/usr/local/lib/python3.14/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 280, in build_wheel
#14 43.91           return _build_backend().build_wheel(
#14 43.91                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
#14 43.91               wheel_directory, config_settings, metadata_directory
#14 43.91               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#14 43.91           )
#14 43.91           ^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/build_meta.py", line 441, in build_wheel
#14 43.91           return _build(['bdist_wheel', '--dist-info-dir', str(metadata_directory)])
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/build_meta.py", line 429, in _build
#14 43.91           return self._build_with_temp_dir(
#14 43.91                  ~~~~~~~~~~~~~~~~~~~~~~~~~^
#14 43.91               cmd,
#14 43.91               ^^^^
#14 43.91           ...<3 lines>...
#14 43.91               self._arbitrary_args(config_settings),
#14 43.91               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#14 43.91           )
#14 43.91           ^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/build_meta.py", line 410, in _build_with_temp_dir
#14 43.91           self.run_setup()
#14 43.91           ~~~~~~~~~~~~~~^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/build_meta.py", line 317, in run_setup
#14 43.91           exec(code, locals())
#14 43.91           ~~~~^^^^^^^^^^^^^^^^
#14 43.91         File "<string>", line 119, in <module>
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/__init__.py", line 117, in setup
#14 43.91           return distutils.core.setup(**attrs)  # type: ignore[return-value]
#14 43.91                  ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/core.py", line 186, in setup
#14 43.91           return run_commands(dist)
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/core.py", line 202, in run_commands
#14 43.91           dist.run_commands()
#14 43.91           ~~~~~~~~~~~~~~~~~^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/dist.py", line 1000, in run_commands
#14 43.91           self.run_command(cmd)
#14 43.91           ~~~~~~~~~~~~~~~~^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/dist.py", line 1107, in run_command
#14 43.91           super().run_command(command)
#14 43.91           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/dist.py", line 1019, in run_command
#14 43.91           cmd_obj.run()
#14 43.91           ~~~~~~~~~~~^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/command/bdist_wheel.py", line 370, in run
#14 43.91           self.run_command("build")
#14 43.91           ~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/cmd.py", line 341, in run_command
#14 43.91           self.distribution.run_command(command)
#14 43.91           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/dist.py", line 1107, in run_command
#14 43.91           super().run_command(command)
#14 43.91           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/dist.py", line 1019, in run_command
#14 43.91           cmd_obj.run()
#14 43.91           ~~~~~~~~~~~^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/command/build.py", line 135, in run
#14 43.91           self.run_command(cmd_name)
#14 43.91           ~~~~~~~~~~~~~~~~^^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/cmd.py", line 341, in run_command
#14 43.91           self.distribution.run_command(command)
#14 43.91           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/dist.py", line 1107, in run_command
#14 43.91           super().run_command(command)
#14 43.91           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/dist.py", line 1019, in run_command
#14 43.91           cmd_obj.run()
#14 43.91           ~~~~~~~~~~~^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/command/build_ext.py", line 97, in run
#14 43.91           _build_ext.run(self)
#14 43.91           ~~~~~~~~~~~~~~^^^^^^
#14 43.91         File "/tmp/pip-build-env-1viia3e8/overlay/lib/python3.14/site-packages/setuptools/_distutils/command/build_ext.py", line 367, in run
#14 43.91           self.build_extensions()
#14 43.91           ~~~~~~~~~~~~~~~~~~~~~^^
#14 43.91         File "<string>", line 106, in build_extensions
#14 43.91         File "<string>", line 70, in cpp_flag
#14 43.91       RuntimeError: Unsupported compiler -- at least C++11 support is needed!
#14 43.91       [end of output]
#14 43.91   
#14 43.91   note: This error originates from a subprocess, and is likely not a problem with pip.
#14 43.91   ERROR: Failed building wheel for chroma-hnswlib
#14 43.91   Building wheel for pydantic-core (pyproject.toml): started
#14 44.50   Building wheel for pydantic-core (pyproject.toml): finished with status 'error'
#14 44.51   error: subprocess-exited-with-error
#14 44.51   
#14 44.51   × Building wheel for pydantic-core (pyproject.toml) did not run successfully.
#14 44.51   │ exit code: 1
#14 44.51   ╰─> [41 lines of output]
#14 44.51       Python reports SOABI: cpython-314-x86_64-linux-gnu
#14 44.51       Computed rustc target triple: x86_64-unknown-linux-gnu
#14 44.51       Installation directory: /root/.cache/puccinialin
#14 44.51       Rustup already downloaded
#14 44.51       Installing rust to /root/.cache/puccinialin/rustup
#14 44.51       warn: It looks like you have an existing rustup settings file at:
#14 44.51       warn: /root/.cache/puccinialin/rustup/settings.toml
#14 44.51       warn: Rustup will install the default toolchain as specified in the settings file,
#14 44.51       warn: instead of the one inferred from the default host triple.
#14 44.51       info: profile set to minimal
#14 44.51       info: setting default host triple to x86_64-unknown-linux-gnu
#14 44.51       warn: Updating existing toolchain, profile choice will be ignored
#14 44.51       info: syncing channel updates for stable-x86_64-unknown-linux-gnu
#14 44.51       info: default toolchain set to stable-x86_64-unknown-linux-gnu
#14 44.51       warn: no default linker (`cc`) was found in your PATH
#14 44.51       warn: many Rust crates require a system C toolchain to build
#14 44.51       Checking if cargo is installed
#14 44.51       cargo 1.96.0 (30a34c682 2026-05-25)
#14 44.51       Rust not found, installing into a temporary directory
#14 44.51       Running `maturin pep517 build-wheel -i /usr/local/bin/python3.14 --compatibility off`
#14 44.51       📦 Including license file `LICENSE`
#14 44.51       🍹 Building a mixed python/rust project
#14 44.51       🐍 Found CPython 3.14 at /usr/local/bin/python3.14
#14 44.51       🔗 Found pyo3 bindings
#14 44.51       📡 Using build options features, bindings from pyproject.toml
#14 44.51          Compiling proc-macro2 v1.0.86
#14 44.51          Compiling unicode-ident v1.0.12

icense file `LICENSE`
#14 44.51       🍹 Building a mixed python/rust project
#14 44.51       🐍 Found CPython 3.14 at /usr/local/bin/python3.14
#14 44.51       🔗 Found pyo3 bindings
#14 44.51       📡 Using build options features, bindings from pyproject.toml
#14 44.51          Compiling proc-macro2 v1.0.86
#14 44.51          Compiling unicode-ident v1.0.12
#14 44.51          Compiling target-lexicon v0.12.14
#14 44.51          Compiling python3-dll-a v0.2.10
#14 44.51          Compiling once_cell v1.19.0
#14 44.51       error: linker `cc` not found
#14 44.51         |
#14 44.51         = note: No such file or directory (os error 2)
#14 44.51       
#14 44.51       error: could not compile `proc-macro2` (build script) due to 1 previous error
#14 44.51       warning: build failed, waiting for other jobs to finish...
#14 44.51       error: could not compile `target-lexicon` (build script) due to 1 previous error
#14 44.51       💥 maturin failed
#14 44.51         Caused by: Failed to build a native library through cargo
#14 44.51         Caused by: Cargo build finished with "exit status: 101": `env -u CARGO PYO3_BUILD_EXTENSION_MODULE="1" PYO3_ENVIRONMENT_SIGNATURE="cpython-3.14-64bit" PYO3_PYTHON="/usr/local/bin/python3.14" PYTHON_SYS_EXECUTABLE="/usr/local/bin/python3.14" "cargo" "rustc" "--profile" "release" "--features" "pyo3/extension-module" "--message-format" "json-render-diagnostics" "--manifest-path" "/tmp/pip-install-a70fs8q1/pydantic-core_0b1bcee826c7463f945e61c0c433d641/Cargo.toml" "--lib" "--crate-type" "cdylib"`
#14 44.51       Error: command ['maturin', 'pep517', 'build-wheel', '-i', '/usr/local/bin/python3.14', '--compatibility', 'off'] returned non-zero exit status 1
#14 44.51       [end of output]
#14 44.51   
#14 44.51   note: This error originates from a subprocess, and is likely not a problem with pip.
#14 44.51   ERROR: Failed building wheel for pydantic-core
#14 44.51   Building wheel for sgmllib3k (pyproject.toml): started
#14 44.69   Building wheel for sgmllib3k (pyproject.toml): finished with status 'done'
#14 44.69   Created wheel for sgmllib3k: filename=sgmllib3k-1.0.0-py3-none-any.whl size=6090 sha256=8211e4183a680c0cecf342b84c22d2eac37dee410343ab7c399ddf9fc6fa1d0d
#14 44.69   Stored in directory: /root/.cache/pip/wheels/e3/43/83/0f6e317d0698ac38ee6a5b6e214019c167057916a11bad91ab
#14 44.69 Successfully built sgmllib3k
#14 44.69 Failed to build asyncpg greenlet pyzmq msgpack chroma-hnswlib pydantic-core
#14 44.69 error: failed-wheel-build-for-install
#14 44.69 
#14 44.69 × Failed to build installable wheels for some pyproject.toml based projects
#14 44.69 ╰─> asyncpg, greenlet, pyzmq, msgpack, chroma-hnswlib, pydantic-core
#14 ERROR: process "/bin/sh -c pip install --default-timeout=1000 --retries=10 --prefix=/install         --extra-index-url https://download.pytorch.org/whl/cpu         -r requirements/base.txt" did not complete successfully: exit code: 1
------
 > [builder 4/8] RUN --mount=type=cache,target=/root/.cache/pip     pip install --default-timeout=1000 --retries=10 --prefix=/install         --extra-index-url https://download.pytorch.org/whl/cpu         -r requirements/base.txt:
44.51   Building wheel for sgmllib3k (pyproject.toml): started
44.69   Building wheel for sgmllib3k (pyproject.toml): finished with status 'done'
44.69   Created wheel for sgmllib3k: filename=sgmllib3k-1.0.0-py3-none-any.whl size=6090 sha256=8211e4183a680c0cecf342b84c22d2eac37dee410343ab7c399ddf9fc6fa1d0d
44.69   Stored in directory: /root/.cache/pip/wheels/e3/43/83/0f6e317d0698ac38ee6a5b6e214019c167057916a11bad91ab
44.69 Successfully built sgmllib3k
44.69 Failed to build asyncpg greenlet pyzmq msgpack chroma-hnswlib pydantic-core
44.69 error: failed-wheel-build-for-install
44.69 
44.69 × Failed to build installable wheels for some pyproject.toml based projects
44.69 ╰─> asyncpg, greenlet, pyzmq, msgpack, chroma-hnswlib, pydantic-core
------
WARNING: No output specified with docker-container driver. Build result will only remain in the build cache. To push result image into registry use --push or to load image into docker use --load
Dockerfile:23
--------------------
  22 |     # CI, so the COPY broke every build in the workflow build matrix.
  23 | >>> RUN --mount=type=cache,target=/root/.cache/pip \
  24 | >>>     pip install --default-timeout=1000 --retries=10 --prefix=/install \
  25 | >>>         --extra-index-url https://download.pytorch.org/whl/cpu \
  26 | >>>         -r requirements/base.txt
  27 |     
--------------------
ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --default-timeout=1000 --retries=10 --prefix=/install         --extra-index-url https://download.pytorch.org/whl/cpu         -r requirements/base.txt" did not complete successfully: exit code: 1
Reference
Check build summary support
Error: buildx failed with: ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --default-timeout=1000 --retries=10 --prefix=/install         --extra-index-url https://download.pytorch.org/whl/cpu         -r requirements/base.txt" did not complete successfully: exit code: 1
