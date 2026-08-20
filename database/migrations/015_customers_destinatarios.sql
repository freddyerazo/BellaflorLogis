-- 015_customers_destinatarios.sql
-- Pobla destinatario en clientes IGUAL e inserta destinatarios DIFER desde dartis_ventas

-- 1. Actualizar destinatario donde cliente = destinatario
UPDATE customers SET destinatario = 'Floral Access', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('Floral Access')
     OR UPPER(TRIM(customer_name)) = UPPER('Floral Access'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'BUDS FLORAL IMPORTS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('BUDS FLORAL IMPORTS')
     OR UPPER(TRIM(customer_name)) = UPPER('BUDS FLORAL IMPORTS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'EVA''S GARDEN FLOWERS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('EVA''S GARDEN FLOWERS')
     OR UPPER(TRIM(customer_name)) = UPPER('EVA''S GARDEN FLOWERS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'FALL RIVER FLORIST SUPPLY COMPANY INC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('FALL RIVER FLORIST SUPPLY COMPANY INC')
     OR UPPER(TRIM(customer_name)) = UPPER('FALL RIVER FLORIST SUPPLY COMPANY INC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'Dalsimer of Boca Raton, Inc', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('Dalsimer of Boca Raton, Inc')
     OR UPPER(TRIM(customer_name)) = UPPER('Dalsimer of Boca Raton, Inc'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'HOLEX USA INC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('HOLEX USA INC')
     OR UPPER(TRIM(customer_name)) = UPPER('HOLEX USA INC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'LD TRADING', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('LD TRADING')
     OR UPPER(TRIM(customer_name)) = UPPER('LD TRADING'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'ALLURE FARMS, Inc.', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('ALLURE FARMS, INC.')
     OR UPPER(TRIM(customer_name)) = UPPER('ALLURE FARMS, INC.'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'IMPORT FLOWERS NASHVILLE', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('IMPORT FLOWERS NASHVILLE')
     OR UPPER(TRIM(customer_name)) = UPPER('IMPORT FLOWERS NASHVILLE'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'Abraflora Wholesale Flowers, LLC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('ABRAFLORA WHOLESALE FLOWERS, LLC')
     OR UPPER(TRIM(customer_name)) = UPPER('ABRAFLORA WHOLESALE FLOWERS, LLC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'HYDROTROPICS CORP. DBA', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('HYDROTROPICS CORP. DBA')
     OR UPPER(TRIM(customer_name)) = UPPER('HYDROTROPICS CORP. DBA'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'DANISA''S WHOLESALE', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('DANISA''S WHOLESALE')
     OR UPPER(TRIM(customer_name)) = UPPER('DANISA''S WHOLESALE'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'Fair Trade Floral Inc', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('Fair Trade Floral Inc')
     OR UPPER(TRIM(customer_name)) = UPPER('Fair Trade Floral Inc'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'FRESCA FARMS LLC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('FRESCA FARMS LLC')
     OR UPPER(TRIM(customer_name)) = UPPER('FRESCA FARMS LLC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'J ROSE WHOLEASALE FLOWERS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('J ROSE WHOLEASALE FLOWERS')
     OR UPPER(TRIM(customer_name)) = UPPER('J ROSE WHOLEASALE FLOWERS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'HIGHLAND C&C LLC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('HIGHLAND C&C LLC')
     OR UPPER(TRIM(customer_name)) = UPPER('HIGHLAND C&C LLC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'FULL POT INTERNATIONAL CORP.', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('FULL POT INTERNATIONAL CORP.')
     OR UPPER(TRIM(customer_name)) = UPPER('FULL POT INTERNATIONAL CORP.'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'Sunburst Farms BDC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('SUNBURST FARMS BDC')
     OR UPPER(TRIM(customer_name)) = UPPER('SUNBURST FARMS BDC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'POTOMAC FLORAL WHOLESALE', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('POTOMAC FLORAL WHOLESALE')
     OR UPPER(TRIM(customer_name)) = UPPER('POTOMAC FLORAL WHOLESALE'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'DELAWARE VALLEY FLORAL GROUP LLC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('DELAWARE VALLEY FLORAL GROUP LLC')
     OR UPPER(TRIM(customer_name)) = UPPER('DELAWARE VALLEY FLORAL GROUP LLC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'ASSOCIATED CUT FLOWERS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('ASSOCIATED CUT FLOWERS')
     OR UPPER(TRIM(customer_name)) = UPPER('ASSOCIATED CUT FLOWERS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'National Floral Supply, LLC.', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('NATIONAL FLORAL SUPPLY, LLC.')
     OR UPPER(TRIM(customer_name)) = UPPER('NATIONAL FLORAL SUPPLY, LLC.'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'GEORGE RALLIS INC.', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('GEORGE RALLIS INC.')
     OR UPPER(TRIM(customer_name)) = UPPER('GEORGE RALLIS INC.'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'MAYESH WHOLESALE FLORIST', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('MAYESH WHOLESALE FLORIST')
     OR UPPER(TRIM(customer_name)) = UPPER('MAYESH WHOLESALE FLORIST'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'BLOOMOLOGY GLOBAL, LLC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('BLOOMOLOGY GLOBAL, LLC')
     OR UPPER(TRIM(customer_name)) = UPPER('BLOOMOLOGY GLOBAL, LLC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'ESPRIT MIAMI, INC C/O LATIN AMERICAN BROKERS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('ESPRIT MIAMI, INC C/O LATIN AMERICAN BROKERS')
     OR UPPER(TRIM(customer_name)) = UPPER('ESPRIT MIAMI, INC C/O LATIN AMERICAN BROKERS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'RED RAVEN LLC, DBA PETALJET', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('RED RAVEN LLC, DBA PETALJET')
     OR UPPER(TRIM(customer_name)) = UPPER('RED RAVEN LLC, DBA PETALJET'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'BREED BROTHERS WHOLESALE', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('BREED BROTHERS WHOLESALE')
     OR UPPER(TRIM(customer_name)) = UPPER('BREED BROTHERS WHOLESALE'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'UNIVERSAL GREENS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('UNIVERSAL GREENS')
     OR UPPER(TRIM(customer_name)) = UPPER('UNIVERSAL GREENS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'SWEET BLOSSOM SA', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('SWEET BLOSSOM SA')
     OR UPPER(TRIM(customer_name)) = UPPER('SWEET BLOSSOM SA'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'EKI LLC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('EKI LLC')
     OR UPPER(TRIM(customer_name)) = UPPER('EKI LLC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'Priority Flower Express', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('PRIORITY FLOWER EXPRESS')
     OR UPPER(TRIM(customer_name)) = UPPER('PRIORITY FLOWER EXPRESS'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'Heinen''s', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('HEINEN''S')
     OR UPPER(TRIM(customer_name)) = UPPER('HEINEN''S'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'MAINLAND FLORAL DISTRIBUTORS LTD', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('MAINLAND FLORAL DISTRIBUTORS LTD')
     OR UPPER(TRIM(customer_name)) = UPPER('MAINLAND FLORAL DISTRIBUTORS LTD'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'REEVES FLORAL PRODUCTS INC', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('REEVES FLORAL PRODUCTS INC')
     OR UPPER(TRIM(customer_name)) = UPPER('REEVES FLORAL PRODUCTS INC'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'PREMIUM FLOWERS CORPORATION', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('PREMIUM FLOWERS CORPORATION')
     OR UPPER(TRIM(customer_name)) = UPPER('PREMIUM FLOWERS CORPORATION'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'HENRY C. ALDERS WHOLESALE FLORIST INC.', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('HENRY C. ALDERS WHOLESALE FLORIST INC.')
     OR UPPER(TRIM(customer_name)) = UPPER('HENRY C. ALDERS WHOLESALE FLORIST INC.'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'J. VAN VLIET', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('J. VAN VLIET')
     OR UPPER(TRIM(customer_name)) = UPPER('J. VAN VLIET'))
  AND destinatario IS NULL;
UPDATE customers SET destinatario = 'BUDS AND BLOOMS', updated_at = now()
  WHERE (UPPER(TRIM(dartis_name)) = UPPER('BUDS AND BLOOMS')
     OR UPPER(TRIM(customer_name)) = UPPER('BUDS AND BLOOMS'))
  AND destinatario IS NULL;

-- 2. Insertar destinatarios distintos al cliente
INSERT INTO customers (customer_code, customer_name, dartis_name, destinatario, active)
VALUES
('DST-UNITEDEV', 'UNITED EVERGREEN FLORAL GREENS INC', 'BLESSED FLOWERS', 'UNITED EVERGREEN FLORAL GREENS INC', true),
('DST-HRD', 'HRD', 'TRADEWINDS INTL LLC', 'HRD', true),
('DST-VALPARAI', 'VALPARAISSOS FARMS LLC TROPICAL ROSES', 'MASNATIVE', 'VALPARAISSOS FARMS LLC TROPICAL ROSES', true),
('DST-FLOWERLI', 'FLOWER LINK LLC-MISSISSIPPI', 'FLOWER LINK LLC', 'FLOWER LINK LLC-MISSISSIPPI', true),
('DST-MLA', 'MLA', 'TRADEWINDS INTL LLC', 'MLA', true),
('DST-DREISBAC', 'DREISBACH - CINCINNATTI', 'DREISBACH WHOLESALE - OHIO', 'DREISBACH - CINCINNATTI', true),
('DST-RIVMAYES', 'RIV - Mayesh Riverside Distribution', 'MAYESH WHOLESALE FLORIST', 'RIV - Mayesh Riverside Distribution', true),
('DST-FLOWER1', 'FLOWER LINK - PENSACOLA', 'FLOWER LINK LLC', 'FLOWER LINK - PENSACOLA', true),
('DST-CORDOVEZ', 'CORDOVEZ COMPANY INC DBA THE FARM BRIDGE -GA', 'CORDOVEZ COMPANY INC DBA THE FARM BRIDGE GA', 'CORDOVEZ COMPANY INC DBA THE FARM BRIDGE -GA', true),
('DST-WFMSOUTH', 'WFM South Distribution', 'WHOLE FOODS MARKET', 'WFM South Distribution', true),
('DST-CHOICEFL', 'CHOICE FLOWER EXCHANGE', 'PERFECT DETAIL', 'CHOICE FLOWER EXCHANGE', true),
('DST-WILDGING', 'WILD GINGER FLOWERS & GIFTS- MI', 'LA HACIENDA FLOWERS INC', 'WILD GINGER FLOWERS & GIFTS- MI', true),
('DST-WFMCHESH', 'WFM Cheshire', 'WHOLE FOODS MARKET', 'WFM Cheshire', true),
('DST-WFMAUROR', 'WFM Aurora', 'WHOLE FOODS MARKET', 'WFM Aurora', true),
('DST-WFMMDWMI', 'WFM MDW MID ATLANTIC WAREHOUSE', 'WHOLE FOODS MARKET', 'WFM MDW MID ATLANTIC WAREHOUSE', true),
('DST-FLORESHL', 'Flores HL - TN', 'LA HACIENDA FLOWERS INC', 'Flores HL - TN', true),
('DST-NEWYORKF', 'New York Flower Group Inc', 'FOUR SEASONS QUALITY B.V.', 'New York Flower Group Inc', true),
('DST-SK', 'S & K', 'TRADEWINDS INTL LLC', 'S & K', true),
('DST-FLOWER2', 'FLOWER LINK LLC-LOUSIANA', 'FLOWER LINK LLC', 'FLOWER LINK LLC-LOUSIANA', true),
('DST-MRSBLOOM', 'MRS Blooms AIR SEA', 'MRS.BLOOMS DIRECT INC', 'MRS Blooms AIR SEA', true),
('DST-DREISB1', 'DREISBACH - LEXINGTON', 'DREISBACH WHOLESALE - OHIO', 'DREISBACH - LEXINGTON', true),
('DST-KSI', 'KSI', 'TRADEWINDS INTL LLC', 'KSI', true),
('DST-AAP', 'AAP', 'TRADEWINDS INTL LLC', 'AAP', true),
('DST-ATORAPEX', 'ATOR Apex Floral Distributors Toronto', 'TRADEWINDS INTL LLC', 'ATOR Apex Floral Distributors Toronto', true),
('DST-EVERYDAY', 'EVERYDAY FLOWERS AND BALLONS', 'LA HACIENDA FLOWERS INC', 'EVERYDAY FLOWERS AND BALLONS', true),
('DST-RVF', 'RVF', 'TRADEWINDS INTL LLC', 'RVF', true),
('DST-AGUILAEX', 'Aguila Export', 'ROSES & BUSINESS', 'Aguila Export', true),
('DST-WFMSOU1', 'WFM Southwest Distribution Manor', 'WHOLE FOODS MARKET', 'WFM Southwest Distribution Manor', true),
('DST-WFMSOU2', 'WFM Southern California Distribution', 'WHOLE FOODS MARKET', 'WFM Southern California Distribution', true)
ON CONFLICT (customer_code) DO NOTHING;
