import os 
import sys
import uuid
import fileinput
import boto3 

region = os.getenv('AWS_REGION')
tg = os.getenv('AWS_IOT_THING_NAME')

try: 

    mac_address = hex(uuid.getnode())
    mac_address = mac_address[2:8] + 'fffe' + mac_address[8:]
    print('the GatewayEui for the gateway will be', mac_address)
    input_file = "./station.conf"
    file_object = open( input_file, 'r+' )
    for line in fileinput.input(input_file):
        file_object.write(line.replace('"routerid": ""', f'"routerid": "{mac_address}"'))
    file_object.close()
    print('routerid configured in station.conf file')

    if os.path.isfile('cups.crt'):
        print('Found credentials in the folder, gateway provisioning step skipped')
        exit(0)

    lora_region =  sys.argv[1]
    print('Lora region for the gateway:', lora_region)
    print('AWS region:', region)
    print('ThingName used for the name of the gateway:', tg)

    iot = boto3.client('iot', region_name= region)
    iotw = boto3.client('iotwireless', region_name= region)



    gateway = None

    try:
        gateway = iotw.get_wireless_gateway(
            Identifier= mac_address,
            IdentifierType= 'GatewayEui'
        )

    except iotw.exceptions.from_code('ResourceNotFoundException'):
        gateway = iotw.create_wireless_gateway(
            Name= tg,
            Description=f'The LoRaWAN Gateway {tg} has been registered using an AWS IoT Greengrass component',
            LoRaWAN={
                'GatewayEui': mac_address,
                'RfRegion': lora_region
            }
        )
    except Exception as e: 
        print(e)
        exit(1)

    # if the gateway is not created, raise an error
    if gateway.get('Id') == None:
        raise ValueError('Error when provisioning the gateway')

    certs = iot.create_keys_and_certificate(
        setAsActive=True
    )  
    cups= iotw.get_service_endpoint(ServiceType = 'CUPS')
    with open('cups.uri', 'w') as f:
        f.write(cups['ServiceEndpoint'])
    with open('cups.trust', 'w') as f:
        f.write(cups['ServerTrust'])
    cert_id= certs['certificateId']
    with open('cups.crt', 'w') as f:
        f.write(certs['certificatePem'])
    with open('cups.key', 'w') as f:
        f.write(certs['keyPair']['PrivateKey'])
    associate_gateway = iotw.associate_wireless_gateway_with_certificate(
        Id= gateway['Id'],
        IotCertificateId= certs['certificateId']
    )
    print(f"The certificate {certs.get('certificateId')} has been associated with the gateway {tg}")

except Exception as e: 
    print(e)
    exit(1)