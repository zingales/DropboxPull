rm function.zip
cd package
zip -r9 ../function.zip .
cd ..
zip -g function.zip lambda_function.py
aws lambda update-function-code --function-name holdmybookSlackBot --zip-file fileb://function.zip
