from setuptools import setup, find_packages

version = '0.0.1'

setup(name='mvvm',
      version=version,
      description='Model-View-ViewModel framework for Python, based on Wx',
      long_description=open('README.rst').read(),
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Topic :: Software Development :: User Interfaces',
          'Topic :: Utilities',
      ],
      author='Bouke Haarsma',
      author_email='bouke@webatoom.nl',
      url='http://github.com/Bouke/mvvm',
      license='MIT',
      packages=find_packages(),
      zip_safe=False,
)
