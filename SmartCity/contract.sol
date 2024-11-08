// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import "hardhat/console.sol";
//import "@openzeppelin/contracts/utils/math/SafeMath.sol";

contract Vote {
    constructor(){
        owner=msg.sender;
    }

    uint nodecount = 0; //등록 노드 수
    address public owner; //스마트컨트렉트 발행자(TA) 주소

    //@ TA(스마트컨트렉 발행자)에게 권한 부여하는 접근제어자
    modifier onlyOwner()  {
    require(msg.sender == owner,"Caller is not owner");
    _;
    }

    //@ 투표 결과 업로드
    event UploadResult(uint,address,uint,string);
   
    //@ 참여 노드 등록 : 0 <- 등록 전 ,1 <- 등록 후
    struct Node{
        uint signin; // 초기값: 0
    }
    //@ 투표,제안 및 중복 투표 관리
    struct Voter{
       // uint weight; // 권한이 있으면 1 (중복 투표 방지)
        uint voted; // 0 <- 제안 또는 투표 전 , 1 <- 제안 또는 투표 이후
    }
    //@ 제안, 투표
    struct Propose {
        uint Sid; // Sensor's identifiable ID
        uint Time; // Media recording time 
        address[] proposer; // 제안자
        string ipfsaddres; // IPFS link : https://ipfs.io/ipfs/bafybeiemxf5abjwjbikoz4mc3a3dla6ual3jsgpdr4cjr3oz3evfyavhwq/wiki/Vincent_van_Gogh.html
        bytes merkleHash; // 0xf117c908948ad7ab51e7dbc6a98d4d7199c24b92602b8844c423f44ac5764c
        uint Count; // 투표 하면 올라가게
        uint proposercount; // 몇번쨰 제안
    }
    
    //@ Voting control: Agreement 에 도달한 시간대에 대해서는 제안 투표,변경 불가능하게 설정
    struct VotingControl {
        uint256 expiration; // 투표 가능 기간 (#######아직 추가 안함) 
        uint agreement; // 0 <- Agreement 에 도달하지 못한 상태, , 1 <- Agreement 에 도달한 상태
        uint selectedproposecount; //Agreement 에 도달한 제안의 순서

    }

    //@ Proposer 별 제안 또는 투표 최신 카운트
    struct LatestProposercount {
        uint latestproposercount;
    }
    //@ node 등록
    mapping (address => Node) public nodes;
    //@ Voter 정보 ( 시간대별(Time) - 주소별(address) - 투표(제안)유무 )
    mapping (uint=> mapping(address => Voter)) public voters;
    //@ 제안자 정보 ( Time - 제안 순서 - 제안정보 )
    mapping ( uint => mapping(uint256 => Propose)) public proposers;
    //@ 시간대별로 제안된 제안 건수 최신화 저장 (Time - 제안된 제안건수)
    mapping ( uint =>LatestProposercount ) public latestproposercount;
    //@ 시간대별 Agreement 에 도달했는지 여부를 할당
    mapping (uint => VotingControl) public votecontrol;

    //mapping (uint256 => uint256) _proposercounter;
    //@ 노드 등록
    function SignIn() public returns(uint) {
       nodes[msg.sender].signin= 1;
       nodecount = nodecount+1; //노드 등록 이후 count 1 증가
       return nodes[msg.sender].signin;
    }    
    //@ 시간대별로, 주소별 권한 관리 ( 투표, 제안 )
    function GetVoteRight (uint Time) public returns(uint){
        require(nodes[msg.sender].signin == 1, 'This node does not join'); // 등록한 주소만 실행가능
        require(votecontrol[Time].agreement ==0,'This time completed Agreement');//Agreement에 도달한 시간대 이후 재 투표 방지
        voters[Time][msg.sender].voted = 1; // 투표(제안 권한 부여)
        return voters[Time][msg.sender].voted;                   
    }
    //@ latest votecount per time
    function showvotecount(uint Time) public view returns(uint){
        return latestproposercount[Time].latestproposercount;
    }
    //@ 등록 노드 수
    function showsignednode() public view returns(uint){
        return nodecount;
    }
    
    //@ Client정보 조회
    function forclient (uint Time)external view returns(uint , uint ,string memory ,bytes memory ){
        require(votecontrol[Time].agreement ==1,'This time has not been completed');//Agreement에 도달한 시간대 이후 재 투표 방지
        return (proposers[Time][votecontrol[Time].selectedproposecount].Sid,proposers[Time][votecontrol[Time].selectedproposecount].Time,proposers[Time][votecontrol[Time].selectedproposecount].ipfsaddres,proposers[Time][votecontrol[Time].selectedproposecount].merkleHash);
     }
    
    //@ 제안, 시간대 time 에 대한 제안 및 투표
    function Proposal(uint Sid, uint Time, string memory ipfsaddres, bytes memory merkleHash)public {
      uint z =0;
      require(votecontrol[Time].agreement ==0,'This time completed Agreement');//Agreement에 도달한 시간대 이후 재 투표 방지
      require(nodes[msg.sender].signin == 1, 'This node does not join'); // join 한 주소인지 확인
      require(voters[Time][msg.sender].voted == 1,'This node does not get right to vote');
      //console.log("test:",latestproposercount[Time].latestproposercount); // 초기값: 0
      //time - 제안 순서를 거꾸로 확인하며, 같은 merklehash가 같으면 count 1 증가
      if( z == 0){
       for (uint i=latestproposercount[Time].latestproposercount; i > 0; ){
        // Byte값 비교는 너무 복잡하여, 그냥 해시 값 같은지 비교
        if(keccak256(abi.encodePacked(proposers[Time][i].merkleHash)) == keccak256(abi.encodePacked(merkleHash))) {
            proposers[Time][i].Count++; // 같은 값이 있다면, count 증가
            proposers[Time][i].proposer.push(msg.sender);
            console.log("Proposer count increase");
            console.log("proposers[Time][i].Count:",proposers[Time][i].Count);
            console.log("latestproposercount_count:",latestproposercount[Time].latestproposercount);   
            z=1; // 이미 있는 투표라서, count만 올릴경우, 아래 if 문 통과 못하게 z=1 변경
            voters[Time][msg.sender].voted = 0; // 투표 또는 제안 권한 박탈

            }
            i--;
        }
        } 
        //신규 제안을 추가
        if(z==0) {       
            latestproposercount[Time].latestproposercount++;//제안 순서 1 증가  
            proposers[Time][latestproposercount[Time].latestproposercount].Sid=Sid;
            proposers[Time][latestproposercount[Time].latestproposercount].Time=Time;
            //proposers[Time][latestproposercount[Time].latestproposercount].proposer=msg.sender;
            proposers[Time][latestproposercount[Time].latestproposercount].proposer.push(msg.sender);
            proposers[Time][latestproposercount[Time].latestproposercount].ipfsaddres=ipfsaddres;
            proposers[Time][latestproposercount[Time].latestproposercount].merkleHash=merkleHash;
            proposers[Time][latestproposercount[Time].latestproposercount].Count=1;//투표값은 1로 초기화
            console.log("New proposer assigned!");
            console.log("latestproposercount_count:",latestproposercount[Time].latestproposercount);
            voters[Time][msg.sender].voted = 0; // 투표 또는 제안 권한 박탈
        }         
    }   
    function queryvoting(uint Time )public view returns(uint){
        return proposers[Time][showvotecount(Time)].Count;
    }
    //using SafeMath for uint256;
    //@ 투표 결정하는 함수 , 51>(동일머클해시보유노드수/총 참여노드수)*100 이면 과반수 
    //@ 투표 결과 조회하여 블록체인에 Agreement 정보 전송 (TA 만 실행 가능)
    function VoteResult(uint Time) public onlyOwner() returns(uint,address,uint,string memory){
        require(votecontrol[Time].agreement ==0,'This time completed Agreement');//Agreement에 도달한 시간대 이후 재 투표 방지
        for (uint i=latestproposercount[Time].latestproposercount; i > 0; ) {
            if (votecontrol[Time].agreement ==0 ) { //이미 Agreement가 이루어진 T 대는 조회 안함
                uint allnode = showsignednode();
                uint b =2;
                //uint target = b.div(allnode); //uint result = b.div(a); // a/b , 버림 
                uint target =allnode/2;
                uint votecount = proposers[Time][i].Count;
                console.log("voteResulttest:", target);
                if(votecount >target ) {
                    console.log("Congratulation! Voting Finish!");
                    console.log("Time:",Time);
                    console.log("Proposer_Address:",proposers[Time][i].proposer[0]);
                    console.log("Sid:",proposers[Time][i].Sid);
                    console.log("IPFS_Adress:",proposers[Time][i].ipfsaddres);
                    console.log("Signed Nodes:",allnode);
                    console.log("Agree Nodes:",votecount);
                    votecontrol[Time].agreement = 1; // Agreement 에 도달하면, 값을  0 -> 1 로 변경
                    votecontrol[Time].selectedproposecount=i; // Agreement 도달한 제안의 순서를 저장 
                    emit UploadResult(Time,proposers[Time][i].proposer[0],proposers[Time][i].Sid,proposers[Time][i].ipfsaddres);
                    for (uint t = 0; t < proposers[Time][i].proposer.length; t++) {
                        erc20transfer(proposers[Time][i].proposer[t],10);
                        console.log("Commision Transfer Complete address:",proposers[Time][i].proposer[t]);
                        console.log("value:",10);                      
                    }
                    
                    return (Time,proposers[Time][i].proposer[0],proposers[Time][i].Sid,proposers[Time][i].ipfsaddres);
                }
            }
            i--;
          }          
        }

          //###### ERC-20 발행 ######

        //@ SmartCityProject 내의 통용되는 총 화폐 /TA가 발행
        erc20BasicForm ERC20 = new erc20BasicForm(100000000); // 1억개 발행
        function erc20mint () public onlyOwner() returns(bool){
            ERC20.mint();
            return true;
        }
        //@ 화폐 이동
        function erc20transfer(address recipient, uint amount) private {
            ERC20.transfer(recipient,amount);
        }
        //@ 계좌별 발란스 조회
        function erc20balance(address account) public view returns(uint256) {
            return ERC20.balanceOf(account);
        }    
        //@ 전체유통량 조회
        function erc20totoalsupply() public view returns (uint256){
            return ERC20.totalSupply();
        }
    }
    contract Search {     
        Vote forclient; 
        function QueryStoredData (address _voteaddr, uint Time) public returns(uint , uint ,string memory ,bytes memory ){
            forclient = Vote(_voteaddr);
            return forclient.forclient(Time);            
        }
    }

//배포안해도 됨
contract erc20BasicForm   {
    mapping ( address => uint256) public _balance;
    mapping (address => mapping(address => uint256)) public _allowances; 
 
    event Transfer(address indexed from, address indexed to, uint256  value);

    uint256 public _totalSupply ; // 총발행량 
    string public _name;  // token 이름
    string public _symbol; // symbol

    constructor (uint256 amount) {
        _name = "SmartCityProject";
        _symbol = "SCP";
        _totalSupply = amount;
        _balance[msg.sender] = amount;
    }

    function mint(   ) public {  
              emit Transfer(address(0),msg.sender,_totalSupply);
    }  

    function name() public view returns (string memory){
        return _name; //토큰 이름 
    }    
    function symbol() public view returns(string memory){
        return _symbol;// 토큰의 심볼
    }
    
    function totalSupply() external view virtual  returns (uint256){
        return _totalSupply; //총발행량
    }
    function balanceOf( address account) external view virtual  returns (uint256){
        return _balance[account]; //owner 가 가지고 있는 토큰의 보유량 확인
    }
     function transfer( address recipient, uint amount) public virtual  returns(bool){
        _transfer(msg.sender,recipient,amount); //전송 함수 실행 
        return true;        
    } 
      function _transfer( address sender, address recipient , uint256 amount) internal virtual {
        require(sender != address(0),"ERC20: transfer from the zero address");
        require(recipient != address(0),"ERC20: transfer to the zero address");
        
        uint256 senderBalance = _balance[sender];
        require(senderBalance >= amount, "ERC20: transfer amount exceeds balance");
       _balance[sender] = senderBalance-amount;
       _balance[recipient] =_balance[recipient]+amount;         
    }    
}