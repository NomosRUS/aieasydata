# Create test datasets for different target databases

Write-Host "Creating test datasets for PostgreSQL and HDFS..." -ForegroundColor Cyan

# Create directory if it doesn't exist
New-Item -ItemType Directory -Path "data_landing_zone/raw" -Force | Out-Null

# PostgreSQL dataset - smaller, more transactional data
$postgresData = @"
id,customer_id,product_name,category,price,quantity,sale_date,payment_method,store_location
1,1001,Office Chair Pro,Furniture,299.99,1,2024-01-15,Credit Card,New York
2,1002,Wireless Keyboard,Electronics,79.99,2,2024-01-15,Debit Card,Los Angeles
3,1003,Standing Desk,Furniture,599.99,1,2024-01-16,Credit Card,Chicago
4,1001,Monitor 27inch,Electronics,399.99,1,2024-01-16,Credit Card,New York
5,1004,Ergonomic Mouse,Electronics,49.99,3,2024-01-17,Cash,Miami
6,1005,Desk Lamp LED,Furniture,89.99,1,2024-01-17,Credit Card,Seattle
7,1002,Notebook Set,Office Supplies,24.99,5,2024-01-18,Debit Card,Los Angeles
8,1006,Coffee Mug,Office Supplies,12.99,2,2024-01-18,Cash,Boston
"@

# HDFS dataset - larger, more analytical data with different structure
$hdfsData = @"
transaction_id,timestamp,user_id,session_id,event_type,product_category,revenue,country,device_type,channel
tx_001,2024-01-15T10:30:00Z,user_12345,sess_abc123,purchase,electronics,1299.99,USA,desktop,organic
tx_002,2024-01-15T11:45:00Z,user_67890,sess_def456,view,furniture,0.00,Canada,mobile,paid_search
tx_003,2024-01-15T14:20:00Z,user_11111,sess_ghi789,purchase,electronics,79.99,UK,tablet,social
tx_004,2024-01-16T09:15:00Z,user_22222,sess_jkl012,cart_add,furniture,0.00,Germany,desktop,email
tx_005,2024-01-16T16:30:00Z,user_33333,sess_mno345,purchase,office_supplies,199.99,France,mobile,organic
tx_006,2024-01-17T12:00:00Z,user_44444,sess_pqr678,view,electronics,0.00,Australia,desktop,direct
tx_007,2024-01-17T18:45:00Z,user_55555,sess_stu901,purchase,furniture,899.99,Japan,mobile,paid_search
tx_008,2024-01-18T08:30:00Z,user_66666,sess_vwx234,checkout,electronics,0.00,Brazil,tablet,social
"@

# Save PostgreSQL dataset
$postgresData | Out-File -FilePath "data_landing_zone/raw/sales_postgres.csv" -Encoding UTF8
Write-Host "[SUCCESS] Created PostgreSQL test dataset (8 records)" -ForegroundColor Green

# Save HDFS dataset  
$hdfsData | Out-File -FilePath "data_landing_zone/raw/sales_hdfs.csv" -Encoding UTF8
Write-Host "[SUCCESS] Created HDFS test dataset (8 records)" -ForegroundColor Green

Write-Host "`nDatasets created:" -ForegroundColor Yellow
Write-Host "  - sales_postgres.csv: Transactional sales data for PostgreSQL" -ForegroundColor Gray
Write-Host "  - sales_hdfs.csv: Event stream data for HDFS" -ForegroundColor Gray
