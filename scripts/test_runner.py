"""
MAIAN CI test runner for Augur project.
"""
import json
import logging
import os
import re
import shutil

from subprocess import check_output

logging.basicConfig(filename='MAIAN-test-result.log', level=logging.INFO)

fail_build = False  # Specifies if to fail the build


def check_failure(test_result):
    """
    Return True if a failure was found.

    :param test_result: test result log.
    :return: True if failure found, false otherwise.
    """
    fail_regexes = ["Confirmed ! The contract is suicidal !",
                    "Confirmed ! The contract is prodigal !",
                    "Leak vulnerability found!",
                    "Locking vulnerability found!",
                    "The code does not have CALL/SUICIDE/DELEGATECALL/CALLCODE thus is greedy !"]
    for fail_regex in fail_regexes:
        if re.search(fail_regex, test_result, re.IGNORECASE):
            return True
    return False


def setup_blockchain(maian_blockchain_dir="/MAIAN/tool/blockchains"):
    """
    Setup private blockchain for the project.

    :param maian_blockchain_dir: path to MAIAN blockchain dir
    :return: -
    """
    if os.path.exists(os.path.join(os.getcwd(), 'blockchains')):
        shutil.rmtree(os.path.join(os.getcwd(), 'blockchains'))
    shutil.copytree(maian_blockchain_dir, os.path.join(os.getcwd(), 'blockchains'))


def run_maian(contract_bytecode_path, mode):
    """
    Run MAIAN tool.

    :param contract_bytecode_path: path to bin contract file
    :param mode: 0 - search for suicidal contracts, 1 - prodigal, 2 - greedy.
    :return: True if vulnerability found. False otherwise.
    """
    vulnerability_found = False
    result = check_output(['python',
                           '/MAIAN/tool/maian.py',
                           '-b',
                           contract_bytecode_path,
                           '-c',
                           mode]).decode("utf-8")
    print(result)

    if check_failure(result):
        vulnerability_found = True

    return vulnerability_found


def extract_augur_contracts_for_analysis(contracts_file_path=
                                         '/app/output/contracts/contracts.json'):
    """
    Extract Augur contracts from contracts.json

    :param contracts_file_path: full path to contracts.json
    :return: a list of paths to files with contracts bytecode
    :rtype: list
    """
    contract_list = []
    with open(contracts_file_path) as f:
        contracts = json.load(f)['contracts']
    for contract_filename in contracts.keys():
        contract_name = contracts[contract_filename].keys()[0]
        contract_bytecode = contracts[contract_filename][contract_name]['evm']['bytecode']['object']
        print("Extracting " + contract_filename + "...")
        if os.path.exists(os.path.join(os.getcwd(), contract_filename)):
            os.remove(os.path.join(os.getcwd(), contract_filename))
        try:
            os.makedirs(os.path.join(os.getcwd(), os.path.dirname(contract_filename)))
        except os.error:
            pass  # folder already exists
        contract_bytecode_path = os.path.join(os.path.dirname(contract_filename), contract_name + '.bin')
        with open(contract_bytecode_path, 'w') as wf:
            wf.write(contract_bytecode)
            print("Contract bytecode written to " + contract_bytecode_path)
            contract_list.append(contract_bytecode_path)
    return contract_list


setup_blockchain()

# Process each file individually and check for suicidal, prodigal and greedy contracts
for file in extract_augur_contracts_for_analysis():

    print("Processing " + file + " for suicidal contracts\n")
    if run_maian(file, '0'):
        fail_build = True

    print("Processing " + file + " for prodigal contracts\n")
    if run_maian(file, '1'):
        fail_build = True

    print("Processing " + file + " for greedy contracts\n")
    if run_maian(file, '2'):
        fail_build = True


if fail_build:
    print("Failing MAIAN test run. Suicidal, prodigal or greedy contracts were found.")
    exit(1)

print("MAIAN test run passed since no security vulnerabilities were found.")
